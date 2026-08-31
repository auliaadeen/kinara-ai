"""AI-001/002/003: valid JSON validates, invalid JSON retries once, then
fails in a controlled way. Mocks the Gemini client entirely — no network.

Multi-Provider AI Architecture Step 1 note: the Gemini SDK client
constructor moved from ai_engine._client (module function) to
GeminiProvider._client (instance method, src/services/ai_providers/
gemini_provider.py) as part of extracting all Gemini-specific logic into
its own provider module. These tests still verify ai_engine.generate_
worksheet's public behavior end-to-end (same AIGenerationError messages,
same call counts) — only the mock's patch target moved to match where the
Gemini client is now actually constructed. Same for the logger name in
the two "is_logged" tests: the logger.exception(...) calls physically
live in gemini_provider.py now, not ai_engine.py.
"""
import json
import logging
from unittest.mock import MagicMock

import pytest

from src.config import Settings
from src.services import ai_engine
from src.services.ai_providers import gemini_provider

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


def _settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
    )


def _fake_client(*responses):
    client = MagicMock()
    client.models.generate_content.side_effect = list(responses)
    return client


def test_valid_json_first_try_no_retry(monkeypatch):
    client = _fake_client(MagicMock(text=VALID_PAYLOAD))
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 1


def test_invalid_json_retries_once_then_succeeds(monkeypatch):
    client = _fake_client(MagicMock(text="not json"), MagicMock(text=VALID_PAYLOAD))
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 2


def test_invalid_json_twice_raises_controlled_error(monkeypatch):
    client = _fake_client(MagicMock(text="not json"), MagicMock(text="still not json"))
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError):
        ai_engine.generate_worksheet(_settings(), "prompt")
    assert client.models.generate_content.call_count == 2


def test_api_failure_raises_immediately_without_retry(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("network down")
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError):
        ai_engine.generate_worksheet(_settings(), "prompt")
    assert client.models.generate_content.call_count == 1


# --- 429 / RESOURCE_EXHAUSTED handling (hardening this rate-limit was
# previously misread as a session-state bug) ---------------------------------


class _FakeRateLimitError(Exception):
    """Mimics the shape google-genai's ClientError actually has for a 429
    (.code, .status attributes) — confirmed via a live diagnostic call,
    not guessed."""

    def __init__(self, message="429 RESOURCE_EXHAUSTED. quota exceeded"):
        super().__init__(message)
        self.code = 429
        self.status = "RESOURCE_EXHAUSTED"


def test_rate_limit_error_detected_via_code_attr_produces_rate_limit_message(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeRateLimitError()
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE
    assert client.models.generate_content.call_count == 1  # no pointless retry


def test_rate_limit_error_detected_via_status_attr_only(monkeypatch):
    class _StatusOnlyError(Exception):
        status = "RESOURCE_EXHAUSTED"

    client = MagicMock()
    client.models.generate_content.side_effect = _StatusOnlyError("some message")
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE


def test_rate_limit_error_detected_via_string_fallback(monkeypatch):
    # No .code/.status attrs at all -- only the message text hints at it,
    # covering an SDK version that shapes the exception differently.
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: quota exceeded")
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE


def test_non_rate_limit_error_still_produces_generic_message(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("connection reset by peer")
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


def test_rate_limit_failure_is_logged(monkeypatch, caplog):
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeRateLimitError()
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with caplog.at_level(logging.ERROR, logger="src.services.ai_providers.gemini_provider"):
        with pytest.raises(ai_engine.AIGenerationError):
            ai_engine.generate_worksheet(_settings(), "prompt")

    assert len(caplog.records) >= 1
    assert any("rate limited" in r.message for r in caplog.records)


def test_generic_failure_is_logged(monkeypatch, caplog):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("connection reset")
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with caplog.at_level(logging.ERROR, logger="src.services.ai_providers.gemini_provider"):
        with pytest.raises(ai_engine.AIGenerationError):
            ai_engine.generate_worksheet(_settings(), "prompt")

    assert len(caplog.records) >= 1


def test_user_facing_message_never_contains_sensitive_payload_content(monkeypatch):
    sensitive_payload = (
        "429 RESOURCE_EXHAUSTED. api key AIzaSyFAKESECRETKEY1234567890, "
        "project kinara-ai-764b6-super-secret, quota metric generate_content_free_tier_requests"
    )
    client = MagicMock()
    client.models.generate_content.side_effect = _FakeRateLimitError(sensitive_payload)
    monkeypatch.setattr(gemini_provider.GeminiProvider, "_client", lambda self: client)

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(), "prompt")

    message = str(exc_info.value)
    assert message == ai_engine.RATE_LIMIT_MESSAGE
    assert "AIzaSy" not in message
    assert "kinara-ai-764b6" not in message
    assert "api key" not in message.lower()
    assert "quota metric" not in message.lower()
