"""OpenAIProvider (Multi-Provider AI Architecture, Step 3A).

Standalone provider tests -- OpenAIProvider is not wired into ai_engine.py
yet. Mocks the `openai` SDK client entirely. No real OpenAI API calls or
network access anywhere in this file: OpenAI(...) is never actually
constructed with a usable client -- _client() is monkeypatched to return
a MagicMock before generate_worksheet() is ever called, and the few real
openai.* exception instances built here are constructed directly in
Python (message + a mocked httpx response object), never received from
a live request.
"""
import json
from unittest.mock import MagicMock

import pytest
from openai import (
    APIConnectionError,
    AuthenticationError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)

from src.config import Settings
from src.services.ai_providers.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    AITransientProviderError,
)
from src.services.ai_providers.openai_provider import OpenAIProvider

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
# required "questions", wrong type for "difficulty") -- exercises the
# Pydantic ValidationError path distinctly from a JSON decode failure.
SCHEMA_INVALID_PAYLOAD = json.dumps({"title": "x", "objective": "y", "difficulty": 123})


def _settings(**overrides) -> Settings:
    values = dict(
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
        openai_api_key="openai-test-key",
        openai_model="gpt-4o-mini",
    )
    values.update(overrides)
    return Settings(**values)


def _fake_completion(content: str | None):
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


def _patched_provider(monkeypatch, client) -> OpenAIProvider:
    monkeypatch.setattr(OpenAIProvider, "_client", lambda self: client)
    return OpenAIProvider(_settings())


def _fake_status_error(cls, status_code: int, message: str = "error"):
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    response.request = MagicMock()
    return cls(message, response=response, body=None)


def _fake_connection_error(message: str = "connection error"):
    return APIConnectionError(message=message, request=MagicMock())


# --- successful generation ---------------------------------------------------


def test_successful_generation_returns_worksheet_response(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_completion(VALID_PAYLOAD)
    provider = _patched_provider(monkeypatch, client)

    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "Fractions Basics"
    assert result.questions[0].concept == "fractions"
    assert client.chat.completions.create.call_count == 1


def test_generation_passes_safety_instruction_and_model(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_completion(VALID_PAYLOAD)
    provider = _patched_provider(monkeypatch, client)

    provider.generate_worksheet("the prompt", "the safety instruction")

    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["messages"][0] == {"role": "system", "content": "the safety instruction"}
    assert kwargs["messages"][1] == {"role": "user", "content": "the prompt"}


# --- malformed / invalid response --------------------------------------------


def test_malformed_json_raises_invalid_response_error_after_retry(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_completion("not json at all"),
        _fake_completion("still not json"),
    ]
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIInvalidResponseError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "openai"
    assert client.chat.completions.create.call_count == 2


def test_schema_invalid_response_raises_invalid_response_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_completion(SCHEMA_INVALID_PAYLOAD),
        _fake_completion(SCHEMA_INVALID_PAYLOAD),
    ]
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIInvalidResponseError):
        provider.generate_worksheet("prompt", "safety instruction")

    assert client.chat.completions.create.call_count == 2


def test_malformed_response_recovers_on_retry(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_completion("not json"),
        _fake_completion(VALID_PAYLOAD),
    ]
    provider = _patched_provider(monkeypatch, client)

    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "Fractions Basics"
    assert client.chat.completions.create.call_count == 2


def test_schema_invalid_response_recovers_on_retry(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_completion(SCHEMA_INVALID_PAYLOAD),
        _fake_completion(VALID_PAYLOAD),
    ]
    provider = _patched_provider(monkeypatch, client)

    result = provider.generate_worksheet("prompt", "safety instruction")

    assert result.title == "Fractions Basics"
    assert client.chat.completions.create.call_count == 2


def test_none_content_treated_as_invalid_response(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_completion(None),
        _fake_completion(None),
    ]
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIInvalidResponseError):
        provider.generate_worksheet("prompt", "safety instruction")


# --- rate-limit conversion -----------------------------------------------------


def test_rate_limit_error_converts_to_ai_rate_limit_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(
        RateLimitError, 429, "rate limit exceeded"
    )
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "openai"
    assert client.chat.completions.create.call_count == 1  # no pointless retry


# --- authentication conversion -------------------------------------------------


def test_authentication_error_converts_to_ai_authentication_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(
        AuthenticationError, 401, "invalid API key"
    )
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    assert exc_info.value.provider == "openai"
    assert client.chat.completions.create.call_count == 1


def test_permission_denied_also_converts_to_ai_authentication_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(
        PermissionDeniedError, 403, "insufficient permissions"
    )
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIAuthenticationError):
        provider.generate_worksheet("prompt", "safety instruction")


# --- configuration errors -------------------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(AIConfigurationError) as exc_info:
        OpenAIProvider(_settings(openai_api_key=""))

    assert exc_info.value.provider == "openai"


def test_missing_model_raises_configuration_error():
    with pytest.raises(AIConfigurationError):
        OpenAIProvider(_settings(openai_model=""))


def test_gemini_only_settings_do_not_satisfy_openai_provider():
    # the whole point of these being separate/optional fields: a
    # Gemini-only Settings (defaults) must not accidentally construct.
    settings = Settings(
        gemini_api_key="k", gemini_model="m", google_cloud_project="p",
        firebase_project_id="p", firebase_web_api_key="w", port=8080,
    )
    with pytest.raises(AIConfigurationError):
        OpenAIProvider(settings)


# --- transient / network / 5xx conversion --------------------------------------


def test_connection_error_converts_to_base_provider_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_connection_error("network unreachable")
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    # Step 3B: this bucket is now the explicit AITransientProviderError
    # subclass so ai_engine.py's fallback dispatcher can identify it by
    # type (errors.py). Still an AIProviderError (pytest.raises above).
    assert type(exc_info.value) is AITransientProviderError
    assert exc_info.value.provider == "openai"


def test_internal_server_error_converts_to_base_provider_error(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(
        InternalServerError, 500, "internal error"
    )
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIProviderError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    # Step 3B: this bucket is now the explicit AITransientProviderError
    # subclass so ai_engine.py's fallback dispatcher can identify it by
    # type (errors.py). Still an AIProviderError (pytest.raises above).
    assert type(exc_info.value) is AITransientProviderError


# --- no secret/payload leakage --------------------------------------------------


def test_no_api_key_appears_in_exception_string(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(
        AuthenticationError, 401, "Incorrect API key provided: sk-FAKESECRETKEY1234567890abcdef"
    )
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIAuthenticationError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    message = str(exc_info.value)
    assert "sk-FAKESECRETKEY1234567890abcdef" not in message
    assert message == "OpenAI rejected the request credentials."


def test_no_sensitive_payload_leakage_in_error_message(monkeypatch):
    sensitive = (
        "429 rate limit. org-secretorgid123, project proj_secretid456, "
        "billing quota metric exceeded for account acct_verysecret"
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = _fake_status_error(RateLimitError, 429, sensitive)
    provider = _patched_provider(monkeypatch, client)

    with pytest.raises(AIRateLimitError) as exc_info:
        provider.generate_worksheet("prompt", "safety instruction")

    message = str(exc_info.value)
    assert "org-secretorgid123" not in message
    assert "proj_secretid456" not in message
    assert "acct_verysecret" not in message


def test_configuration_error_never_contains_key_value():
    with pytest.raises(AIConfigurationError) as exc_info:
        OpenAIProvider(_settings(openai_api_key=""))
    assert "sk-" not in str(exc_info.value)


# --- protocol conformance -------------------------------------------------------


def test_openai_provider_conforms_to_ai_provider_protocol():
    # AIProvider is a plain (non-runtime_checkable) typing.Protocol, so
    # conformance is checked structurally here rather than via isinstance()
    # -- matches how OpenAIProvider/GeminiProvider are actually consumed
    # (duck-typed, never isinstance-checked, by ai_engine.py).
    provider = OpenAIProvider(_settings())
    assert hasattr(provider, "name") and isinstance(provider.name, str)
    assert callable(getattr(provider, "generate_worksheet", None))
    assert provider.name == "openai"
