"""OpenAI provider (Multi-Provider AI Architecture, Step 3A).

Standalone implementation of the AIProvider contract (base.py), using the
official `openai` Python SDK — no raw HTTP. NOT wired into ai_engine.py's
dispatcher yet: Gemini remains the only provider actually selected by
default (config.py's AI_PRIMARY_PROVIDER), and there is no fallback logic
anywhere yet. This module exists so it can be exercised/tested on its own
before any dispatch policy touches it.

Mirrors GeminiProvider's shape deliberately: same validation contract
(JSON response -> json.loads -> WorksheetResponse.model_validate), same
retry-once-on-invalid-response behavior, same provider-neutral error
mapping, same "never log/expose a key or raw payload" discipline.
"""
from __future__ import annotations

import copy
import json
import logging

from openai import OpenAI
from openai import AuthenticationError as OpenAIAuthenticationError
from openai import PermissionDeniedError as OpenAIPermissionDeniedError
from openai import RateLimitError as OpenAIRateLimitError
from pydantic import ValidationError

from src.config import Settings
from src.models.ai_schemas import WorksheetResponse
from src.services.ai_providers.base import AIProvider
from src.services.ai_providers.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIRateLimitError,
    AITransientProviderError,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

# OpenAI's strict structured-output mode (response_format:
# {"type": "json_schema", "json_schema": {..., "strict": True}}) requires
# EVERY object node in the schema to explicitly set
# additionalProperties: false — confirmed live: OpenAI returns
# "400 Invalid schema ... 'additionalProperties' is required to be
# supplied and to be false" without it. Pydantic's model_json_schema()
# doesn't add this by default. WorksheetResponse.model_json_schema()
# stays the single source of truth; this only post-processes a copy of
# its output for OpenAI specifically — Gemini's response_schema usage
# (gemini_provider.py) is untouched and doesn't go through this at all.


def _with_additional_properties_false(schema: dict) -> dict:
    """Return a deep copy of `schema` with additionalProperties: false set
    on every object-type node — root, $defs/definitions entries, and any
    nested object reachable through properties/items/anyOf/allOf/oneOf.
    Never mutates the input (callers, including tests, can compare against
    the original safely)."""
    node = copy.deepcopy(schema)
    _force_additional_properties_false(node)
    return node


def _force_additional_properties_false(node: object) -> None:
    if isinstance(node, list):
        for item in node:
            _force_additional_properties_false(item)
        return

    if not isinstance(node, dict):
        return

    if node.get("type") == "object" or "properties" in node:
        node["additionalProperties"] = False

    for key in ("properties", "$defs", "definitions"):
        container = node.get(key)
        if isinstance(container, dict):
            for value in container.values():
                _force_additional_properties_false(value)

    if "items" in node:
        _force_additional_properties_false(node["items"])

    for key in ("anyOf", "allOf", "oneOf"):
        if key in node:
            _force_additional_properties_false(node[key])


_WORKSHEET_JSON_SCHEMA = {
    "name": "worksheet_response",
    "schema": _with_additional_properties_false(WorksheetResponse.model_json_schema()),
    "strict": True,
}


class OpenAIProvider(AIProvider):
    """Implements AIProvider for OpenAI via the official `openai` SDK."""

    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise AIConfigurationError("OpenAI API key is not configured.", provider=self.name)
        if not settings.openai_model:
            raise AIConfigurationError("OpenAI model is not configured.", provider=self.name)
        self._settings = settings

    def _client(self) -> OpenAI:
        return OpenAI(api_key=self._settings.openai_api_key)

    def generate_worksheet(self, prompt: str, safety_instruction: str) -> WorksheetResponse:
        client = self._client()
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.chat.completions.create(
                    model=self._settings.openai_model,
                    messages=[
                        {"role": "system", "content": safety_instruction},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_schema", "json_schema": _WORKSHEET_JSON_SCHEMA},
                )
            except Exception as exc:  # network / API failure — no point retrying immediately
                # Log the real exception either way — never silently discard
                # it (same convention as GeminiProvider / firestore_service.py).
                if isinstance(exc, OpenAIRateLimitError):
                    logger.exception(
                        "OpenAI call failed (%s): %s", "rate limited / quota exhausted", exc
                    )
                    raise AIRateLimitError(
                        "OpenAI is rate-limited or its quota is exhausted.", provider=self.name
                    ) from exc
                if isinstance(exc, (OpenAIAuthenticationError, OpenAIPermissionDeniedError)):
                    logger.exception(
                        "OpenAI call failed (%s): %s", "authentication/authorization error", exc
                    )
                    raise AIAuthenticationError(
                        "OpenAI rejected the request credentials.", provider=self.name
                    ) from exc
                logger.exception("OpenAI call failed (%s): %s", "unexpected API/network error", exc)
                # Everything that isn't a recognized rate-limit or auth
                # failure is treated as plausibly transient (network error,
                # timeout, 5xx) — this is the exact bucket Step 3B's
                # fallback dispatcher is allowed to retry via another
                # provider (ai_providers/errors.py::AITransientProviderError).
                raise AITransientProviderError("OpenAI call failed.", provider=self.name) from exc

            content = response.choices[0].message.content
            if content is None:
                last_error = ValueError("OpenAI returned no content")
                continue

            try:
                data = json.loads(content)
                return WorksheetResponse.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                continue

        raise AIInvalidResponseError(
            "OpenAI returned an unusable response twice in a row.", provider=self.name
        ) from last_error
