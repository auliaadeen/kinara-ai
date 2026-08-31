"""Provider-neutral AI errors (Multi-Provider AI Architecture, Step 1).

ai_engine.py catches these and translates them into the existing, public
AIGenerationError with a safe static message — session_service.py and the
UI never see these directly and never need to change. Provider modules
(gemini_provider.py today; others later) raise these instead of leaking
raw SDK exception types, so a future second provider can map its own
SDK's errors into the exact same vocabulary without ai_engine.py knowing
which provider actually ran.

Every message constructed here must be safe to show a user or write to a
log: never build one from a raw exception's str() if that exception could
contain a key, project id, or quota identifier — keep it to short, static,
human-written text.
"""
from __future__ import annotations


class AIProviderError(RuntimeError):
    """Base for every provider-neutral AI error. Carries which provider
    raised it (a short name like "gemini"), never the raw SDK payload."""

    def __init__(self, message: str, provider: str):
        super().__init__(message)
        self.provider = provider


class AIRateLimitError(AIProviderError):
    """Provider is temporarily rate-limited / quota exhausted (e.g. Gemini
    429 RESOURCE_EXHAUSTED). Recoverable — a caller may retry later, or
    (a later step) fall back to a different provider."""


class AIAuthenticationError(AIProviderError):
    """Provider rejected the request's credentials (invalid/revoked API
    key, insufficient permissions). Not recoverable by retrying the same
    provider with the same credentials."""


class AIConfigurationError(AIProviderError):
    """Provider is missing required configuration (e.g. no API key or
    model set) — a setup problem, not a runtime API failure."""


class AIInvalidResponseError(AIProviderError):
    """Provider returned content that didn't parse as JSON or didn't
    validate against WorksheetResponse, even after the provider's own
    internal retry."""


class AITransientProviderError(AIProviderError):
    """A provider call failed for a reason that is plausibly transient —
    network error, request timeout, 5xx server error — as opposed to
    something a different provider or a retry wouldn't fix (auth,
    configuration, malformed request/response). Added in Step 3B
    specifically so ai_engine.py's fallback dispatcher can identify
    transient failures explicitly by type, rather than guessing from
    exception strings. Together with AIRateLimitError, this is the only
    error type eligible for cross-provider fallback."""
