"""Provider-agnostic AI contract (Multi-Provider AI Architecture, Step 1).

Any provider (Gemini today; others later, e.g. OpenAI in a future step)
implements this. ai_engine.py — and every piece of Kinara's actual
learning/business logic (session_service.py, adaptive_engine.py,
gamification.py, Firestore, the UI) — never needs to know which provider
is actually running (AI_SPEC.md §0). The return type is always the
existing WorksheetResponse (src/models/ai_schemas.py); there is no
separate provider-layer response format to keep in sync with it.
"""
from __future__ import annotations

from typing import Protocol

from src.models.ai_schemas import WorksheetResponse


class AIProvider(Protocol):
    """name: short identifier for logs (e.g. "gemini"). Not used to branch
    any learning/business logic outside this package."""

    name: str

    def generate_worksheet(self, prompt: str, safety_instruction: str) -> WorksheetResponse:
        """Generate one worksheet from a fully-built prompt.

        Must raise one of the AIProviderError subclasses (errors.py) on
        failure — never a raw provider SDK exception, so callers never
        need to know or import a specific SDK's exception types.
        """
        ...
