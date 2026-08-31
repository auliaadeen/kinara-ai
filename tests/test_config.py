"""src/config.py -- Multi-Provider AI Architecture, Step 2 additions.

AI_PRIMARY_PROVIDER / AI_FALLBACK_PROVIDER must default cleanly so every
existing Gemini-only .env keeps working unchanged (no new required
variable). Uses monkeypatch on os.environ, not a real .env file.
"""
from src.config import load_settings

_REQUIRED_ENV = {
    "GEMINI_API_KEY": "test-key",
    "GOOGLE_CLOUD_PROJECT": "proj",
    "FIREBASE_PROJECT_ID": "proj",
    "FIREBASE_WEB_API_KEY": "web-key",
}


def _set_required_env(monkeypatch):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    # Make sure a real local .env's provider vars (if any) don't leak into
    # a test that wants to see the *default* behavior.
    monkeypatch.delenv("AI_PRIMARY_PROVIDER", raising=False)
    monkeypatch.delenv("AI_FALLBACK_PROVIDER", raising=False)


def test_existing_gemini_only_env_remains_valid(monkeypatch):
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.gemini_api_key == "test-key"
    assert settings.google_cloud_project == "proj"


def test_ai_primary_provider_defaults_to_gemini(monkeypatch):
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.ai_primary_provider == "gemini"


def test_ai_fallback_provider_defaults_to_none(monkeypatch):
    _set_required_env(monkeypatch)

    settings = load_settings()

    assert settings.ai_fallback_provider == "none"


def test_ai_primary_provider_reads_from_env_and_normalizes_case(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("AI_PRIMARY_PROVIDER", "  GEMINI  ")

    settings = load_settings()

    assert settings.ai_primary_provider == "gemini"


def test_ai_fallback_provider_reads_from_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("AI_FALLBACK_PROVIDER", "OpenAI")

    settings = load_settings()

    assert settings.ai_fallback_provider == "openai"
