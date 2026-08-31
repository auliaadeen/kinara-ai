"""Multi-Provider AI Architecture, Step 3B — fallback dispatch policy in
ai_engine.generate_worksheet.

Every provider here is a plain in-memory stub (_StubProvider) — this file
never imports or touches GeminiProvider or OpenAIProvider, and never
constructs a real `google.genai` or `openai` client. Zero real network
calls, zero real API keys, zero Gemini quota consumed. GeminiProvider's
and OpenAIProvider's own internals are covered separately in
tests/test_ai_providers_gemini.py and tests/test_ai_providers_openai.py;
this file is purely about the dispatch/fallback *policy*.
"""
import inspect

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
    AITransientProviderError,
)

GEMINI_RESULT = WorksheetResponse(
    title="From Gemini",
    objective="Practice fractions",
    difficulty="easy",
    questions=[
        {
            "id": "1",
            "prompt": "1/2 of 4?",
            "options": ["1", "2"],
            "correct_answer_index": 1,
            "concept": "fractions",
        }
    ],
)

OPENAI_RESULT = WorksheetResponse(
    title="From OpenAI",
    objective="Practice fractions",
    difficulty="easy",
    questions=[
        {
            "id": "1",
            "prompt": "1/2 of 4?",
            "options": ["1", "2"],
            "correct_answer_index": 1,
            "concept": "fractions",
        }
    ],
)


def _settings(**overrides) -> Settings:
    values = dict(
        gemini_api_key="gemini-test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
        ai_primary_provider="gemini",
        ai_fallback_provider="none",
    )
    values.update(overrides)
    return Settings(**values)


class _StubProvider:
    """A minimal AIProvider stand-in with a call counter, so tests can
    assert exactly how many times (and in what order) each provider was
    actually invoked."""

    def __init__(self, name: str, result=None, error: Exception | None = None):
        self.name = name
        self._result = result
        self._error = error
        self.calls = 0

    def generate_worksheet(self, prompt, safety_instruction):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result


def _make_get_provider(providers: dict):
    """Stands in for ai_providers.factory.get_provider: same signature,
    same "unsupported name fails explicitly" behavior, but resolves from
    a plain dict of stubs instead of constructing real providers."""

    def get_provider(settings, provider_name=None):
        name = (provider_name or settings.ai_primary_provider or "gemini").strip().lower()
        if name not in providers:
            raise AIConfigurationError(f"Unsupported AI provider: '{name}'.", provider=name)
        return providers[name]

    return get_provider


def _install(monkeypatch, providers: dict):
    monkeypatch.setattr(ai_engine, "get_provider", _make_get_provider(providers))


# --- A. primary success ---------------------------------------------------------


def test_primary_success_fallback_not_called(monkeypatch):
    gemini = _StubProvider("gemini", result=GEMINI_RESULT)
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    result = ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert result is GEMINI_RESULT
    assert gemini.calls == 1
    assert openai_stub.calls == 0


# --- B. rate limit -> fallback success -----------------------------------------


def test_gemini_rate_limit_falls_back_to_openai_success(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    result = ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert result is OPENAI_RESULT
    assert gemini.calls == 1
    assert openai_stub.calls == 1


# --- C. transient failure -> fallback success ----------------------------------


def test_gemini_transient_failure_falls_back_to_openai_success(monkeypatch):
    gemini = _StubProvider(
        "gemini", error=AITransientProviderError("network error", provider="gemini")
    )
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    result = ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert result is OPENAI_RESULT
    assert gemini.calls == 1
    assert openai_stub.calls == 1


# --- D. authentication failure: no fallback ------------------------------------


def test_gemini_authentication_failure_never_falls_back(monkeypatch):
    gemini = _StubProvider("gemini", error=AIAuthenticationError("bad key", provider="gemini"))
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert openai_stub.calls == 0
    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


# --- E. configuration failure: no fallback --------------------------------------


def test_gemini_configuration_failure_at_construction_never_falls_back(monkeypatch):
    """get_provider() itself raises before any provider object exists
    (e.g. AI_PRIMARY_PROVIDER misconfigured) -- fallback must not even be
    considered, since there's no primary failure mode to inspect yet."""
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"openai": openai_stub})  # "gemini" deliberately absent

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert openai_stub.calls == 0
    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


def test_gemini_configuration_failure_during_generation_never_falls_back(monkeypatch):
    gemini = _StubProvider(
        "gemini", error=AIConfigurationError("model not configured", provider="gemini")
    )
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError):
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert openai_stub.calls == 0


# --- F. invalid response: no fallback --------------------------------------------


def test_gemini_invalid_response_never_falls_back(monkeypatch):
    gemini = _StubProvider(
        "gemini", error=AIInvalidResponseError("bad json twice", provider="gemini")
    )
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert openai_stub.calls == 0
    assert str(exc_info.value) == ai_engine.INVALID_RESPONSE_MESSAGE


# --- G. fallback disabled ---------------------------------------------------------


def test_fallback_disabled_preserves_existing_rate_limit_message(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="none"), "prompt")

    assert openai_stub.calls == 0
    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE


# --- H. fallback itself fails -----------------------------------------------------


def test_fallback_also_fails_returns_safe_error_with_exactly_two_attempts(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    openai_stub = _StubProvider(
        "openai", error=AIRateLimitError("also rate limited, org=secretorg123", provider="openai")
    )
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert gemini.calls == 1
    assert openai_stub.calls == 1
    message = str(exc_info.value)
    assert message == ai_engine.RATE_LIMIT_MESSAGE
    assert "secretorg123" not in message


# --- I. same provider as fallback --------------------------------------------------


def test_same_provider_as_fallback_is_not_called_twice(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    _install(monkeypatch, {"gemini": gemini})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(
            _settings(ai_primary_provider="gemini", ai_fallback_provider="gemini"), "prompt"
        )

    assert gemini.calls == 1  # not retried against itself
    assert str(exc_info.value) == ai_engine.RATE_LIMIT_MESSAGE


# --- J. unsupported fallback provider ----------------------------------------------


def test_unsupported_fallback_provider_fails_safely_without_looping(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    _install(monkeypatch, {"gemini": gemini})  # "typo-provider" not registered

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="typo-provider"), "prompt")

    assert gemini.calls == 1  # exactly one primary attempt, no loop back
    assert str(exc_info.value) == ai_engine.GENERIC_FAILURE_MESSAGE


# --- K. no secret leakage -----------------------------------------------------------


def test_no_secret_leakage_in_final_error_message(monkeypatch):
    sensitive_gemini = "429 quota exceeded. api key AIzaSyFAKEKEY1234567890"
    sensitive_openai = "401 unauthorized. api key sk-FAKEOPENAIKEY1234567890abcdef"
    gemini = _StubProvider("gemini", error=AIRateLimitError(sensitive_gemini, provider="gemini"))
    openai_stub = _StubProvider(
        "openai", error=AIAuthenticationError(sensitive_openai, provider="openai")
    )
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    with pytest.raises(ai_engine.AIGenerationError) as exc_info:
        ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    message = str(exc_info.value)
    assert "AIzaSy" not in message
    assert "sk-FAKEOPENAIKEY" not in message


# --- L. session/persistence integrity ------------------------------------------------


def test_generate_worksheet_returns_exactly_one_response_via_fallback(monkeypatch):
    gemini = _StubProvider("gemini", error=AIRateLimitError("rate limited", provider="gemini"))
    openai_stub = _StubProvider("openai", result=OPENAI_RESULT)
    _install(monkeypatch, {"gemini": gemini, "openai": openai_stub})

    result = ai_engine.generate_worksheet(_settings(ai_fallback_provider="openai"), "prompt")

    assert isinstance(result, WorksheetResponse)
    assert gemini.calls == 1
    assert openai_stub.calls == 1  # exactly one fallback attempt, not more


def test_ai_engine_module_never_references_firestore_or_session_state():
    """ai_engine.py must stay pure generation logic -- persistence is
    entirely session_service.py's responsibility, called exactly once by
    its own caller regardless of which provider (or how many attempts)
    answered here."""
    # Note: ai_engine.py legitimately imports the LearningMemory *model*
    # (a plain data structure) as a type hint for build_worksheet_prompt's
    # parameter -- that's unrelated to persistence and predates Step 3B.
    # What must never appear is anything that actually reads/writes state.
    source = inspect.getsource(ai_engine)
    forbidden = [
        "FirestoreService",
        "firestore_service",
        "create_session",
        "complete_session",
        "save_learning_memory",
        "session_state",
    ]
    for term in forbidden:
        assert term not in source, f"ai_engine.py must not reference {term!r}"
