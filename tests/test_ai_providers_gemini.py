"""GeminiProvider (Multi-Provider AI Architecture, Step 1).

Tests GeminiProvider directly -- the provider-neutral errors it raises,
not ai_engine.py's translation of them into AIGenerationError (that's
covered in tests/test_ai_engine.py). No real network calls.
"""
import json
from unittest.mock import MagicMock

import pytest

from src.config import Settings
from src.services.ai_providers.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    AITransientProviderError,
)
from src.services.ai_providers.gemini_provider import GeminiProvider

VALID_PAYLOAD = json.dumps(
    {
        "title": "Fractions Basics",
        "objective": "Identify fractions",
        "difficulty": "easy",
        "questions": [
            {
                "id": "1",
                "prompt": "What is 1/2 of 4?",
                "options": ["1", "2", "3"],
                "correct_answer_index": 1,
                "concept": "fractions",
            }
        ],
    }
)

# Valid JSON, but does not satisfy WorksheetResponse's schema (missing
# required "questions" and wrong type for "difficulty") -- distinct from
# a JSON *decode* failure, exercises the Pydantic ValidationError path.
SCHEMA_INVALID_PAYLOAD = json.dumps({"title": "x", "objective": "y", "difficulty": 123})


def _settings(**overrides) -> Settings:
    values = dict(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
    )
    values.update(overrides)
    return Settings(**values)


class _FakeRateLimitError(Exception):
    def __init__(self, message="429 RESOURCE_EXHAUSTED. quota exceeded"):
        super().__init__(message)
        self.code = 429
        self.status = "RESOURCE_EXHAUSTED"


class _FakeAuthError(Exception):
    def __init__(self, message="401 UNAUTHENTICATED. invalid API key"):
        super().__init__(message)
        self.code = 401
        self.status = "UNAUTHENTICATED"


def _patched_provider(monkeypatch, client) -> GeminiProvider:
    monkeypatch.setattr(GeminiProvider, "_client", lambda self: client)
    return GeminiProvider(_settings())


# --- successful generation ---------------------------------------------------


def test_successful_generation_returns_worksheet_response(monkeypatch):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=VALID_PAYLOAD)
    provider = _patched_provider(monkeypatch, client)

    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 1


# --- malformed / invalid response --------------------------------------------


def test_malformed_json_raises_invalid_response_error_after_retry(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = [
        MagicMock(text="not json at all"),
        MagicMock(text="still not json"),
    ]
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIInvalidResponseError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "gemini"
    assert client.models.generate_content.call_count == 2


def test_schema_invalid_response_raises_invalid_response_error(monkeypatch):
    """Valid JSON, but fails Pydantic validation against WorksheetResponse
    -- distinct failure mode from a JSON decode error."""
    client = MagicMock()
    client.models.generate_content.side_effect = [
        MagicMock(text=SCHEMA_INVALID_PAYLOAD),
        MagicMock(text=SCHEMA_INVALID_PAYLOAD),
    ]
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIInvalidResponseError):
        provider.generate_worksheet("prompt", "safety instruction")

    assert client.models.generate_content.call_count == 2


def test_invalid_response_recovers_on_retry(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = [
        MagicMock(text=SCHEMA_INVALID_PAYLOAD),
        MagicMock(text=VALID_PAYLOAD),
    ]
    provider = _patched_provider(monkeypatch, client)

    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 2


# --- rate-limit conversion -----------------------------------------------------


def test_rate_limit_error_converts_to_ai_rate_limit_error(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeRateLimitError()
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "gemini"
    assert client.models.generate_content.call_count == 1  # no pointless retry


# --- authentication / configuration conversion --------------------------------


def test_authentication_error_converts_to_ai_authentication_error(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeAuthError()
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "gemini"
    assert client.models.generate_content.call_count == 1


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(AIConfigurationError) as exc_info:
        GeminiProvider(_settings(gemini_api_key=""))

    assert exc_info.value.provider == "gemini"


def test_missing_model_raises_configuration_error():
    with pytest.raises(AIConfigurationError):
        GeminiProvider(_settings(gemini_model=""))


def test_unrecognized_exception_converts_to_base_provider_error(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("connection reset by peer")
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    # Step 3B: this bucket (rate-limit/auth ruled out) is now the
    # explicit AITransientProviderError subclass, not the bare base
    # class — that's what lets ai_engine.py's fallback dispatcher
    # identify it by type instead of guessing (errors.py). Still an
    # AIProviderError (pytest.raises above still holds).
    assert type(exc_info.value) is AITransientProviderError
    assert exc_info.value.provider == "gemini"


# --- no secret/payload leakage --------------------------------------------------


def test_error_messages_never_expose_sensitive_payload_content(monkeypatch):
    sensitive_payload = (
        "429 RESOURCE_EXHAUSTED. api key AIzaSyFAKESECRETKEY1234567890, "
        "project kinara-ai-764b6-super-secret, quota metric generate_content_free_tier_requests"
    )
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeRateLimitError(sensitive_payload)
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    message = str(exc_info.value)
    assert "AIzaSy" not in message
    assert "kinara-ai-764b6" not in message
    assert "api key" not in message.lower()
    assert "quota metric" not in message.lower()


def test_configuration_error_message_never_contains_key_value():
    # a present (non-empty) key must construct cleanly
    GeminiProvider(_settings(gemini_api_key="AIzaSyREALLOOKINGSECRETVALUE"))

    # the negative case: an empty key's error message names the problem,
    # never a key value (nothing to leak here, but guard the shape anyway)
    with pytest.raises(AIConfigurationError) as exc_info:
        GeminiProvider(_settings(gemini_api_key=""))
    assert "AIzaSy" not in str(exc_info.value)
