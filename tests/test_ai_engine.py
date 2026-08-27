"""AI-001/002/003: valid JSON validates, invalid JSON retries once, then
fails in a controlled way. Mocks the Gemini client entirely — no network."""
import json
from unittest.mock import MagicMock

import pytest

from src.config import Settings
from src.services import ai_engine

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
    monkeypatch.setattr(ai_engine, "_client", lambda settings: client)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 1


def test_invalid_json_retries_once_then_succeeds(monkeypatch):
    client = _fake_client(MagicMock(text="not json"), MagicMock(text=VALID_PAYLOAD))
    monkeypatch.setattr(ai_engine, "_client", lambda settings: client)

    result = ai_engine.generate_worksheet(_settings(), "prompt")

    assert result.title == "Fractions Basics"
    assert client.models.generate_content.call_count == 2


def test_invalid_json_twice_raises_controlled_error(monkeypatch):
    client = _fake_client(MagicMock(text="not json"), MagicMock(text="still not json"))
    monkeypatch.setattr(ai_engine, "_client", lambda settings: client)

    with pytest.raises(ai_engine.AIGenerationError):
        ai_engine.generate_worksheet(_settings(), "prompt")
    assert client.models.generate_content.call_count == 2


def test_api_failure_raises_immediately_without_retry(monkeypatch):
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("network down")
    monkeypatch.setattr(ai_engine, "_client", lambda settings: client)

    with pytest.raises(ai_engine.AIGenerationError):
        ai_engine.generate_worksheet(_settings(), "prompt")
    assert client.models.generate_content.call_count == 1
