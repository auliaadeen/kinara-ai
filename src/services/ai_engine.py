"""Gemini integration (AI_SPEC.md).

Gemini generates worksheet CONTENT only. It never scores, never touches
Firestore, never decides XP or difficulty progression (AI_SPEC.md #5,
ARCHITECTURE.md #3). Every response is JSON-mode + Pydantic validated
(AI_SPEC.md #2); invalid output is retried once, then fails in a controlled
way (AI_SPEC.md #8, AI-001/002/003).
"""
from __future__ import annotations

import json

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.config import Settings
from src.models.child import Child
from src.models.learning_memory import LearningMemory
from src.models.ai_schemas import WorksheetResponse
from src.services.adaptive_engine import GenerationContext

SAFETY_INSTRUCTION = (
    "You generate short educational worksheets for children and self-learners. "
    "Content must be age-appropriate, free of harmful or unsafe material, and must "
    "never request personal information from the learner (SECURITY.md, AI_SPEC.md #7). "
    "Only claim a learner is strong or weak in a concept when the provided evidence "
    "supports it. Never invent learning history that was not given to you."
)

MAX_ATTEMPTS = 2


class AIGenerationError(RuntimeError):
    """Raised when Gemini fails or returns unusable output after retry (FSD.md #12)."""


def _client(settings: Settings) -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


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


def generate_worksheet(settings: Settings, prompt: str) -> WorksheetResponse:
    client = _client(settings)
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SAFETY_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=WorksheetResponse,
                ),
            )
        except Exception as exc:  # network / API failure — no point retrying immediately
            raise AIGenerationError(
                "Kinara could not reach the AI service. Please try again."
            ) from exc

        try:
            data = json.loads(response.text)
            return WorksheetResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            continue

    raise AIGenerationError(
        "Kinara's AI service returned an unusable response twice in a row. "
        "Please try again in a moment."
    ) from last_error
