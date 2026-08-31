"""Provider factory (Multi-Provider AI Architecture, Step 2; wired to
OpenAI in Step 5A.1).

The ONLY place that maps a provider *name* (a plain string from config)
to a concrete provider class. ai_engine.py and everything above it only
ever deal with the AIProvider protocol, never a provider name or a
specific provider class — this is what keeps Kinara's learning/business
logic (session_service.py, adaptive_engine.py, gamification.py) fully
unaware of which provider is active (AI_SPEC.md §0).

"gemini" and "openai" are both implemented. Any other name is not
silently substituted with Gemini: selecting an unsupported provider is a
configuration error, not a soft fallback. This is what makes an invalid
AI_PRIMARY_PROVIDER/AI_FALLBACK_PROVIDER value fail explicitly rather
than quietly keep working on Gemini and hiding the misconfiguration.

This module is responsible for provider construction/selection only —
deciding *when* to use a fallback provider is ai_engine.py's job, not
this one's.
"""
from __future__ import annotations

from src.config import Settings
from src.services.ai_providers.base import AIProvider
from src.services.ai_providers.errors import AIConfigurationError
from src.services.ai_providers.gemini_provider import GeminiProvider
from src.services.ai_providers.openai_provider import OpenAIProvider


def get_provider(settings: Settings, provider_name: str | None = None) -> AIProvider:
    """Return the AIProvider for `provider_name`, defaulting to
    settings.ai_primary_provider. Exposed as a parameter — rather than
    always reading settings.ai_primary_provider directly — so
    ai_engine.py's fallback dispatcher can ask this same factory for a
    specific *other* provider (e.g. the fallback one) without changing
    this function.
    """
    name = (provider_name or settings.ai_primary_provider or "gemini").strip().lower()

    if name == "gemini":
        return GeminiProvider(settings)

    if name == "openai":
        return OpenAIProvider(settings)

    raise AIConfigurationError(f"Unsupported AI provider: '{name}'.", provider=name)
