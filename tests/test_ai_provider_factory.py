"""Provider factory (Multi-Provider AI Architecture, Step 2; wired to
OpenAI in Step 5A.1).

get_provider(settings) is the only place a provider *name* (a plain
string) turns into a concrete provider class. No real network calls --
constructing OpenAIProvider/GeminiProvider here never calls out to
either SDK, it only builds the client wrapper object.
"""
import pytest

from src.config import Settings
from src.services.ai_providers.errors import AIConfigurationError
from src.services.ai_providers.factory import get_provider
from src.services.ai_providers.gemini_provider import GeminiProvider
from src.services.ai_providers.openai_provider import OpenAIProvider


def _settings(**overrides) -> Settings:
    values = dict(
        gemini_api_key="test-key",
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


def test_default_configuration_selects_gemini_provider():
    settings = _settings()  # ai_primary_provider not passed -> dataclass default
    assert settings.ai_primary_provider == "gemini"

    provider = get_provider(settings)

    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"


def test_explicit_gemini_selects_gemini_provider():
    settings = _settings(ai_primary_provider="gemini")

    provider = get_provider(settings)

    assert isinstance(provider, GeminiProvider)


def test_explicit_gemini_uppercase_still_selects_gemini_provider():
    # config.py lowercases AI_PRIMARY_PROVIDER when loading from env, but
    # the factory itself should not depend on the caller having done that.
    settings = _settings(ai_primary_provider="GEMINI")

    provider = get_provider(settings)

    assert isinstance(provider, GeminiProvider)


def test_openai_is_not_silently_mapped_to_gemini():
    # Step 5A.1: OpenAI is now genuinely implemented and wired -- the
    # thing this test actually guards against is "openai" quietly
    # resolving to GeminiProvider (which would silently mask a real
    # AI_FALLBACK_PROVIDER=openai misconfiguration by always answering
    # with Gemini). It must resolve to a real, distinct OpenAIProvider.
    settings = _settings(ai_primary_provider="openai")

    provider = get_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert not isinstance(provider, GeminiProvider)
    assert provider.name == "openai"


def test_unsupported_provider_name_raises_configuration_error():
    settings = _settings(ai_primary_provider="some-made-up-provider")

    with pytest.raises(AIConfigurationError) as exc_info:
        get_provider(settings)

    assert "unsupported" in str(exc_info.value).lower()
    assert exc_info.value.provider == "some-made-up-provider"


def test_explicit_provider_name_argument_overrides_settings():
    # settings says gemini, but the explicit provider_name argument wins
    # -- this is exactly the mechanism ai_engine.py's fallback dispatcher
    # relies on to request the *fallback* provider by name.
    settings = _settings(ai_primary_provider="gemini")

    provider = get_provider(settings, provider_name="openai")

    assert isinstance(provider, OpenAIProvider)


def test_openai_provider_is_genuinely_imported_in_the_factory_module():
    # Step 5A.1: the factory must actually import and construct
    # OpenAIProvider now -- the old "no openai anywhere" assertion here
    # was true only because the wiring was still missing.
    import inspect

    from src.services.ai_providers import factory

    source = inspect.getsource(factory)
    assert "OpenAIProvider" in source


# --- explicit regression coverage (Step 5A.1) --------------------------------


def test_get_provider_gemini_by_name_returns_gemini_provider():
    settings = _settings(ai_primary_provider="openai")  # deliberately different default

    provider = get_provider(settings, provider_name="gemini")

    assert isinstance(provider, GeminiProvider)


def test_get_provider_openai_by_name_returns_openai_provider():
    settings = _settings(ai_primary_provider="gemini")  # deliberately different default

    provider = get_provider(settings, provider_name="openai")

    assert isinstance(provider, OpenAIProvider)


def test_get_provider_unsupported_name_still_raises_configuration_error():
    settings = _settings()

    with pytest.raises(AIConfigurationError) as exc_info:
        get_provider(settings, provider_name="not-a-real-provider")

    assert exc_info.value.provider == "not-a-real-provider"
