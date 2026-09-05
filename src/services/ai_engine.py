"""AI generation facade (AI_SPEC.md)."""
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

RATE_LIMIT_MESSAGE = "Zunara's AI service is temporarily rate-limited. Please try again later."
GENERIC_FAILURE_MESSAGE = "Zunara could not reach the AI service. Please try again."
INVALID_RESPONSE_MESSAGE = (
    "Zunara's AI service returned an unusable response twice in a row. "
    "Please try again in a moment."
)


class AIGenerationError(RuntimeError):
    """Raised when the AI provider fails or returns unusable output after retry."""


def build_worksheet_prompt(
    child: Child,
    memory: LearningMemory,
    context: GenerationContext,
    topic: str,
    recent_scores: list[float],
) -> str:
    lines = ["Learner:", f"{child.educational_level}", ""]
    if context.has_history:
        lines += [
            "Previous performance (recent scores, oldest first):",
            ", ".join(f"{s:.0f}%" for s in recent_scores) or "none recorded", "",
            "Weak concepts:",
            ", ".join(c.replace("_", " ") for c in memory.weak_concepts) or "none", "",
            "Strong concepts:",
            ", ".join(c.replace("_", " ") for c in memory.strong_concepts) or "none", "",
            "Learning trend:", memory.learning_trend, "",
        ]
    else:
        lines += ["No previous learning history exists for this learner.", ""]
    lines += [
        "Recommended difficulty:", context.difficulty, "",
        "Focus concepts for this activity:",
        ", ".join(c.replace("_", " ") for c in context.focus_concepts) or f"introduce {topic}", "",
        "Task:",
        f'Generate one short multiple-choice worksheet about "{topic}" at "{context.difficulty}" difficulty for this learner, targeting the focus concepts above. 3 to 6 questions, each with 2 to 4 options and exactly one correct option. Use short, normalized, lowercase, underscore-separated concept slugs (e.g. "comparing_fractions") for each question\'s concept field.',
    ]
    return "\n".join(lines)


def _is_fallback_eligible(exc: AIProviderError) -> bool:
    return isinstance(exc, (AIRateLimitError, AITransientProviderError))


def _failure_reason_label(exc: AIProviderError) -> str:
    if isinstance(exc, AIRateLimitError):
        return "rate limit"
    if isinstance(exc, AITransientProviderError):
        return "transient failure"
    return "provider error"


def _safe_message_for(exc: AIProviderError) -> str:
    if isinstance(exc, AIRateLimitError):
        return RATE_LIMIT_MESSAGE
    if isinstance(exc, AIInvalidResponseError):
        return INVALID_RESPONSE_MESSAGE
    return GENERIC_FAILURE_MESSAGE


def generate_worksheet(settings: Settings, prompt: str) -> WorksheetResponse:
    try:
        primary = get_provider(settings)
    except AIProviderError as exc:
        raise AIGenerationError(_safe_message_for(exc)) from exc
    logger.info("AI generation using provider=%s", primary.name)
    try:
        return primary.generate_worksheet(prompt, SAFETY_INSTRUCTION)
    except AIProviderError as primary_exc:
        if not _is_fallback_eligible(primary_exc):
            raise AIGenerationError(_safe_message_for(primary_exc)) from primary_exc
        fallback_name = (settings.ai_fallback_provider or "none").strip().lower()
        reason = _failure_reason_label(primary_exc)
        if not fallback_name or fallback_name == "none" or fallback_name == primary.name:
            logger.info("Primary provider=%s failed (%s); no eligible fallback configured", primary.name, reason)
            raise AIGenerationError(_safe_message_for(primary_exc)) from primary_exc
        logger.info("Primary provider=%s failed (%s); trying fallback=%s", primary.name, reason, fallback_name)
        try:
            fallback = get_provider(settings, provider_name=fallback_name)
            result = fallback.generate_worksheet(prompt, SAFETY_INSTRUCTION)
        except AIProviderError as fallback_exc:
            logger.warning("Fallback provider=%s failed (%s)", fallback_name, _failure_reason_label(fallback_exc))
            raise AIGenerationError(_safe_message_for(fallback_exc)) from fallback_exc
        logger.info("Fallback provider=%s succeeded", fallback_name)
        return result
