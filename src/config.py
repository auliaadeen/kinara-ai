"""Environment configuration for Kinara AI.

Single place to read env vars. No hard-coded secrets, no hard-coded model
selection (AI_SPEC.md #1).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing (AI_RULES Rule 12)."""


# Fallback only — GEMINI_MODEL should always be set explicitly in .env /
# Cloud Run env vars. Update this single constant if the default ever goes
# stale (AI_SPEC.md #1: never hard-code the model elsewhere in the codebase).
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

# Multi-Provider AI Architecture, Step 2: which provider ai_engine.py's
# factory selects. Gemini is the only one implemented — "none" fallback
# means no fallback is attempted (that's a later step, not this one).
DEFAULT_AI_PRIMARY_PROVIDER = "gemini"
DEFAULT_AI_FALLBACK_PROVIDER = "none"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    google_cloud_project: str
    firebase_project_id: str
    firebase_web_api_key: str
    port: int
    # Defaulted (not required) so every existing Gemini-only .env, and
    # every existing Settings(...) construction in tests, keeps working
    # unchanged — these two fields are additive only.
    ai_primary_provider: str = DEFAULT_AI_PRIMARY_PROVIDER
    ai_fallback_provider: str = DEFAULT_AI_FALLBACK_PROVIDER
    # Multi-Provider AI Architecture, Step 3A: OpenAI as a standalone
    # provider (not wired into fallback yet). Empty string, not required —
    # OpenAI is not selected by default, so a Gemini-only .env must never
    # need these. OpenAIProvider itself raises AIConfigurationError if
    # either is empty at construction time (only when OpenAI is actually
    # selected/constructed). No default model value here on purpose — a
    # guessed model name would violate "do not assume gpt-4o-mini".
    openai_api_key: str = ""
    openai_model: str = ""


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            "Set it in your .env (local) or Cloud Run environment/Secret Manager (deployed)."
        )
    return value


def load_settings() -> Settings:
    return Settings(
        gemini_api_key=_require("GEMINI_API_KEY"),
        gemini_model=os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip(),
        google_cloud_project=_require("GOOGLE_CLOUD_PROJECT"),
        firebase_project_id=_require("FIREBASE_PROJECT_ID"),
        firebase_web_api_key=_require("FIREBASE_WEB_API_KEY"),
        port=int(os.environ.get("PORT", "8080")),
        # Not required — an unset .env (every existing one) resolves to
        # the Gemini-only defaults above, unchanged behavior.
        ai_primary_provider=os.environ.get("AI_PRIMARY_PROVIDER", DEFAULT_AI_PRIMARY_PROVIDER)
        .strip()
        .lower(),
        ai_fallback_provider=os.environ.get("AI_FALLBACK_PROVIDER", DEFAULT_AI_FALLBACK_PROVIDER)
        .strip()
        .lower(),
        # Not required — absent in every existing Gemini-only .env, and
        # that must keep working unchanged.
        openai_api_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "").strip(),
    )
