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


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    google_cloud_project: str
    firebase_project_id: str
    firebase_web_api_key: str
    port: int


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
    )
