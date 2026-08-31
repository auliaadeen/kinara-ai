"""Gemini provider (Multi-Provider AI Architecture, Step 1).

Everything google-genai-SDK-specific lives here — the rest of Kinara only
ever sees the AIProvider contract (base.py) and the provider-neutral
errors (errors.py). Extracted from ai_engine.py with no intended
behavioral change: same SDK usage, same model configuration, same
response schema, same JSON + Pydantic validation, same retry-once-on-
invalid-JSON, same rate-limit detection, same safety-instruction
handling — just relocated, and mapped to provider-neutral errors instead
of raising AIGenerationError directly (ai_engine.py does that mapping
now, see its own docstring).
"""
from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
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


def _is_rate_limit_error(exc: Exception) -> bool:
    """Detect Gemini rate-limit/quota exhaustion (HTTP 429 RESOURCE_EXHAUSTED)
    robustly rather than string-matching alone: prefer the structured
    attributes the google-genai client sets on its error objects (.code,
    .status), and fall back to matching the status text in str(exc) in
    case a different SDK version doesn't expose them the same way. This
    exact shape (.code == 429, .status == "RESOURCE_EXHAUSTED") was
    confirmed against the real API during this project, not guessed."""
    if getattr(exc, "code", None) == 429:
        return True
    if str(getattr(exc, "status", "")).upper() == "RESOURCE_EXHAUSTED":
        return True
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def _is_auth_error(exc: Exception) -> bool:
    """Detect an authentication/authorization failure (invalid or revoked
    API key, insufficient permissions) — same structured-attributes-then-
    string-fallback approach as _is_rate_limit_error. Unlike the 429 case,
    this hasn't been reproduced against the live API in this project (a
    valid key was always used), so the string fallback is intentionally
    broad; narrow it if a real Gemini auth failure is ever observed and
    turns out to be shaped differently."""
    code = getattr(exc, "code", None)
    if code in (401, 403):
        return True
    status = str(getattr(exc, "status", "")).upper()
    if status in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
        return True
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "401",
            "403",
            "unauthenticated",
            "permission_denied",
            "api_key_invalid",
            "api key not valid",
        )
    )


class GeminiProvider(AIProvider):
    """Implements AIProvider for Gemini via the google-genai SDK."""

    name = "gemini"

    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise AIConfigurationError("Gemini API key is not configured.", provider=self.name)
        if not settings.gemini_model:
            raise AIConfigurationError("Gemini model is not configured.", provider=self.name)
        self._settings = settings

    def _client(self) -> genai.Client:
        return genai.Client(api_key=self._settings.gemini_api_key)

    def generate_worksheet(self, prompt: str, safety_instruction: str) -> WorksheetResponse:
        client = self._client()
        last_error: Exception | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=safety_instruction,
                        response_mime_type="application/json",
                        response_schema=WorksheetResponse,
                    ),
                )
            except Exception as exc:  # network / API failure — no point retrying immediately
                # Log the real exception either way — never silently discard
                # it (this is exactly what made an earlier 429 misread as a
                # session-state bug: same convention as
                # firestore_service.py's logger.exception calls).
                if _is_rate_limit_error(exc):
                    logger.exception(
                        "Gemini call failed (%s): %s", "rate limited / quota exhausted", exc
                    )
                    raise AIRateLimitError(
                        "Gemini is rate-limited or its quota is exhausted.", provider=self.name
                    ) from exc
                if _is_auth_error(exc):
                    logger.exception(
                        "Gemini call failed (%s): %s", "authentication/authorization error", exc
                    )
                    raise AIAuthenticationError(
                        "Gemini rejected the request credentials.", provider=self.name
                    ) from exc
                logger.exception("Gemini call failed (%s): %s", "unexpected API/network error", exc)
                # Everything that isn't a recognized rate-limit or auth
                # failure is treated as plausibly transient (network error,
                # timeout, 5xx) — this is the exact bucket Step 3B's
                # fallback dispatcher is allowed to retry via another
                # provider (ai_providers/errors.py::AITransientProviderError).
                raise AITransientProviderError("Gemini call failed.", provider=self.name) from exc

            try:
                data = json.loads(response.text)
                return WorksheetResponse.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                continue

        raise AIInvalidResponseError(
            "Gemini returned an unusable response twice in a row.", provider=self.name
        ) from last_error
