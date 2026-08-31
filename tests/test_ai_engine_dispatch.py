"""ai_engine.generate_worksheet as a dispatcher over the provider factory
(Multi-Provider AI Architecture, Step 2). Verifies ai_engine.py delegates
through get_provider() rather than constructing GeminiProvider itself,
and that the existing AIGenerationError contract/messages are unchanged
regardless of that indirection. No real network calls.

Distinct from tests/test_ai_engine.py (which still verifies Gemini's
specific retry/rate-limit/message behavior end-to-end through the real
factory) and tests/test_ai_providers_gemini.py (GeminiProvider in
isolation) -- this file is about the dispatch/selection wiring itself.
"""
import json

import pytest

from src.config import Settings
from src.models.ai_schemas import WorksheetResponse
from src.services import ai_engine
from src.services.ai_providers.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
)

VALID_WORKSHEET = WorksheetResponse(
    title="Fractions Basics",
    objective="Identify fractions",
    difficulty="easy",
    questions=[
        {
            "id": "1",
            "prompt": "What is 1/2 of 4?",
            "options": ["1", "2"],
            "correct_answer_index": 1,
            "concept": "fractions",
        }
    ],
)


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


class _StubProvider:
    """A minimal AIProvider stand-in -- proves ai_engine.py only depends
    on the AIProvider contract, not on GeminiProvider specifically."""

    name = "stub"

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls = 0

    def generate_worksheet(self, prompt, safety_instruction):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result


def test_dispatch_delegates_to_the_factory_selected_provider(monkeypatch):
    stub = _StubProvider(result=VALID_WORKSHEET)
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result is VALID_WORKSHEET
    assert stub.calls == 1


def test_worksheet_response_returned_unchanged(monkeypatch):
    stub = _StubProvider(result=VALID_WORKSHEET)
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == VALID_WORKSHEET.title
    assert result.questions == VALID_WORKSHEET.questions


def test_rate_limit_error_translated_to_existing_contract(monkeypatch):
    stub = _StubProvider(error=AIRateLimitError("rate limited", provider="stub"))
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE


def test_invalid_response_error_translated_to_existing_contract(monkeypatch):
    stub = _StubProvider(error=AIInvalidResponseError("bad json", provider="stub"))
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.INVALID_RESPONSE_MESSAGE


def test_authentication_error_translated_to_generic_safe_message(monkeypatch):
    stub = _StubProvider(error=AIAuthenticationError("bad key", provider="stub"))
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


def test_configuration_error_from_factory_translated_to_generic_safe_message(monkeypatch):
    # e.g. AI_PRIMARY_PROVIDER=openai -- factory raises before any provider
    # is even constructed; ai_engine.py must still produce the existing
    # safe contract, not a raw AIConfigurationError.
    def raise_configuration_error(settings):
        raise AIConfigurationError("AI provider 'openai' is not yet implemented.", provider="openai")

    monkeypatch.setattr(ai_engine, "get_provider", raise_configuration_error)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_primary_provider="openai"), "prompt")

    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


def test_generic_provider_error_translated_to_generic_safe_message(monkeypatch):
    stub = _StubProvider(error=AIProviderError("network down", provider="stub"))
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


def test_error_message_never_contains_provider_internal_detail(monkeypatch):
    sensitive = "401 UNAUTHENTICATED api key AIzaSyFAKESECRET1234567890 project kinara-ai-764b6"
    stub = _StubProvider(error=AIAuthenticationError(sensitive, provider="stub"))
    monkeypatch.setattr(ai_engine, "get_provider", lambda settings: stub)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    message = str(exc_info.value)
    assert "AIzaSy" not in message
    assert "kinara-ai-764b6" not in message


def test_real_factory_still_resolves_gemini_by_default(monkeypatch):
    """End-to-end through the *real* factory (not stubbed) -- proves the
    default wiring (no AI_PRIMARY_PROVIDER override) still reaches
    GeminiProvider, exactly like Step 1, just via the factory now."""
    from src.services.ai_providers.gemini_provider import GeminiProvider

    client = None

    def fake_client(self):
        nonlocal client
        import unittest.mock as mock

        client = mock.MagicMock()
        client.models.generate_content.return_value = mock.MagicMock(
            text=json.dumps(
                {
                    "title": "T",
                    "objective": "O",
                    "difficulty": "easy",
                    "questions": [
                        {
                            "id": "1",
                            "prompt": "P",
                            "options": ["a", "b"],
                            "correct_answer_index": 0,
                            "concept": "c",
                        }
                    ],
                }
            )
        )
        return client

    monkeypatch.setattr(GeminiProvider, "_client", fake_client)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == "T"
