"""AI generation facade (AI_SPEC.md).

Public entry point the rest of Kinara calls (session_service.py, and
AIGenerationError is also imported directly by src/ui/session_launch.py).
Callers never need to know which AI provider actually generated the
content, or whether a fallback happened (Multi-Provider AI Architecture —
Step 1 extracted Gemini into its own provider module; Step 2 added the
provider factory; Step 3B, here, adds a single controlled fallback
attempt). Gemini is still the default; OpenAI is only ever used as a
configured fallback, never automatically preferred or substituted.

Whichever provider ends up answering generates worksheet CONTENT only. It
never scores, never touches Firestore, never decides XP or difficulty
progression (AI_SPEC.md #5, ARCHITECTURE.md #3) — and neither does this
module: generate_worksheet returns exactly one WorksheetResponse or
raises AIGenerationError, nothing else, regardless of which provider (or
how many attempts) it took to get there. Persistence stays entirely
session_service.py's job, called exactly once by its caller either way.
Every response is JSON-mode + Pydantic validated (AI_SPEC.md #2); invalid
output is retried once *by the provider itself*, then fails in a
controlled way (AI_SPEC.md #8, AI-001/002/003) — that retry behavior is
unchanged and is not where fallback happens.
"""
from __future__ import annotations

import logging

from src.config import Settings
from src.models.child import Child
from src.models.learning_memory import LearningMemory
from src.models.ai_schemas import WorksheetResponse
from src.services.adaptive_engine import GenerationContext
from src.services.ai_providers.errors import (
    AIInvalidResponseError,
    AIProviderError,
    AIRateLimitError,
    AITransientProviderError,
)
from src.services.ai_providers.factory import get_provider

logger = logging.getLogger(__name__)

SAFETY_INSTRUCTION = (
    "You generate short educational worksheets for children and self-learners. "
    "Content must be age-appropriate, free of harmful or unsafe material, and must "
    "never request personal information from the learner (SECURITY.md, AI_SPEC.md #7). "
    "Only claim a learner is strong or weak in a concept when the provided evidence "
    "supports it. Never invent learning history that was not given to you."
)

# Static, safe user-facing messages only — never built from a raw provider
# exception, so an error payload (which can mention quota metrics, project
# identifiers, etc.) never reaches the UI. Provider-neutral: written about
# "Kinara's AI service", not any specific provider by name.
RATE_LIMIT_MESSAGE = "Kinara's AI service is temporarily rate-limited. Please try again later."
GENERIC_FAILURE_MESSAGE = "Kinara could not reach the AI service. Please try again."
INVALID_RESPONSE_MESSAGE = (
    "Kinara's AI service returned an unusable response twice in a row. "
    "Please try again in a moment."
)


class AIGenerationError(RuntimeError):
    """Raised when the AI provider fails or returns unusable output after
    retry (FSD.md #12). Public — session_service.py and the UI catch this
    specifically; they never see provider-neutral errors or provider SDK
    exceptions directly."""


def build_worksheet_prompt(
    child: Child,
    memory: LearningMemory,
    context: GenerationContext,
    topic: str,
    recent_scores: list[float],
) -> str:
    """AI_SPEC.md #3, #4: always send contextual evidence, never a bare
    prompt, whenever history exists."""
    lines = [
        "Learner:",
        f"{child.educational_level}",
        "",
    ]

    if context.has_history:
        lines += [
            "Previous performance (recent scores, oldest first):",
            ", ".join(f"{s:.0f}%" for s in recent_scores) or "none recorded",
            "",
            "Weak concepts:",
            ", ".join(c.replace("_", " ") for c in memory.weak_concepts) or "none",
            "",
            "Strong concepts:",
            ", ".join(c.replace("_", " ") for c in memory.strong_concepts) or "none",
            "",
            "Learning trend:",
            memory.learning_trend,
            "",
        ]
    else:
        lines += ["No previous learning history exists for this learner.", ""]

    lines += [
        "Recommended difficulty:",
        context.difficulty,
        "",
        "Focus concepts for this activity:",
        ", ".join(c.replace("_", " ") for c in context.focus_concepts) or f"introduce {topic}",
        "",
        "Task:",
        f'Generate one short multiple-choice worksheet about "{topic}" at "{context.difficulty}" '
        "difficulty for this learner, targeting the focus concepts above. 3 to 6 questions, "
        "each with 2 to 4 options and exactly one correct option. Use short, normalized, "
        'lowercase, underscore-separated concept slugs (e.g. "comparing_fractions") for each '
        "question's concept field.",
    ]
    return "\n".join(lines)


def _is_fallback_eligible(exc: AIProviderError) -> bool:
    """Only these are worth trying a different provider for. Everything
    else (authentication, configuration, or an invalid response even
    after the provider's own retry) fails immediately: a different
    provider wouldn't fix a bad key or a bad request, and silently
    masking those would hide a real problem instead of surfacing it."""
    return isinstance(exc, (AIRateLimitError, AITransientProviderError))


def _failure_reason_label(exc: AIProviderError) -> str:
    """Safe, content-free label for logs — derived only from the
    exception's type, never its message (which may carry provider-
    specific detail)."""
    if isinstance(exc, AIRateLimitError):
        return "rate limit"
    if isinstance(exc, AITransientProviderError):
        return "transient failure"
    return "provider error"


def _safe_message_for(exc: AIProviderError) -> str:
    """Map any provider-neutral error to the existing safe user-facing
    message. Never built from the raw exception — static strings only,
    so nothing provider-specific (quota metrics, project ids, request
    detail) can reach the UI."""
    if isinstance(exc, AIRateLimitError):
        return RATE_LIMIT_MESSAGE
    if isinstance(exc, AIInvalidResponseError):
        return INVALID_RESPONSE_MESSAGE
    return GENERIC_FAILURE_MESSAGE


def generate_worksheet(settings: Settings, prompt: str) -> WorksheetResponse:
    """Primary provider first (default: Gemini, via the factory). On
    AIRateLimitError or a transient provider failure, try the configured
    fallback provider exactly once — never on authentication,
    configuration, or invalid-response failures, and never more than
    primary -> fallback -> final failure (no loops back to primary).
    session_service.py, adaptive_engine.py, and the UI never change to
    add this — they only ever call this one function and only ever see
    a WorksheetResponse or AIGenerationError, exactly as before."""
    try:
        primary = get_provider(settings)
    except AIProviderError as exc:
        raise AIGenerationError(_safe_message_for(exc)) from exc

    # Provider identity only — never the prompt (may contain learner
    # context) and never any credential/setting value.
    logger.info("AI generation using provider=%s", primary.name)

    try:
        return primary.generate_worksheet(prompt, SAFETY_INSTRUCTION)
    except AIProviderError as primary_exc:
        if not _is_fallback_eligible(primary_exc):
            raise AIGenerationError(_safe_message_for(primary_exc)) from primary_exc

        fallback_name = (settings.ai_fallback_provider or "none").strip().lower()
        reason = _failure_reason_label(primary_exc)

        if not fallback_name or fallback_name == "none" or fallback_name == primary.name:
            logger.info(
                "Primary provider=%s failed (%s); no eligible fallback configured",
                primary.name,
                reason,
            )
            raise AIGenerationError(_safe_message_for(primary_exc)) from primary_exc

        logger.info(
            "Primary provider=%s failed (%s); trying fallback=%s", primary.name, reason, fallback_name
        )
        try:
            fallback = get_provider(settings, provider_name=fallback_name)
            result = fallback.generate_worksheet(prompt, SAFETY_INSTRUCTION)
        except AIProviderError as fallback_exc:
            logger.warning(
                "Fallback provider=%s failed (%s)",
                fallback_name,
                _failure_reason_label(fallback_exc),
            )
            raise AIGenerationError(_safe_message_for(fallback_exc)) from fallback_exc

        logger.info("Fallback provider=%s succeeded", fallback_name)
        return result
