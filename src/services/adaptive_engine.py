"""Adaptive Engine (FSD.md #8, #9; ARCHITECTURE.md #3).

Pure, deterministic rules for difficulty/focus. Runs entirely in Python —
Gemini never decides difficulty progression (AI_SPEC.md #5). No I/O, fully
unit-testable (AI_RULES Rule 8).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.models.common import Difficulty, step_difficulty
from src.models.learning_memory import LearningMemory

SCORE_LOW = 60.0
SCORE_HIGH = 80.0


@dataclass
class GenerationContext:
    """What the AI Engine needs before asking Gemini for a new activity."""

    difficulty: Difficulty
    focus_concepts: list[str] = field(default_factory=list)
    has_history: bool = False


@dataclass
class NextExperience:
    topic: str
    difficulty: Difficulty
    objective: str
    reason: str


def build_generation_context(
    memory: LearningMemory, requested_difficulty: Difficulty | None
) -> GenerationContext:
    """Used right before calling Gemini (FSD.md #3.3 steps 1-4).

    If the learner has prior history, it MUST shape the request
    (AI_RULES Rule 7 / SESSION-001, MEMORY-003).
    """
    difficulty = requested_difficulty or memory.recommended_difficulty
    return GenerationContext(
        difficulty=difficulty,
        focus_concepts=list(memory.weak_concepts),
        has_history=memory.has_history,
    )


def next_difficulty(previous_difficulty: Difficulty, score: float) -> Difficulty:
    """FSD.md #8 thresholds (ADAPT-001/002/003)."""
    if score < SCORE_LOW:
        step = -1
    elif score < SCORE_HIGH:
        step = 0
    else:
        step = 1
    return step_difficulty(previous_difficulty, step)


def priority_weak_concept(
    previous_weak_concepts: list[str], this_session_incorrect_concepts: list[str]
) -> str | None:
    """ADAPT-004: a concept missed again after already being weak gets
    priority over other weak concepts."""
    for concept in this_session_incorrect_concepts:
        if concept in previous_weak_concepts:
            return concept
    return None


def build_next_experience(
    *, updated_memory: LearningMemory, last_topic: str, repeated_weak_concept: str | None
) -> NextExperience:
    """FSD.md #9. Reason text is built from actual stored evidence only —
    never invented (AI_SPEC.md #5)."""
    difficulty = updated_memory.recommended_difficulty

    if repeated_weak_concept:
        topic = last_topic
        objective = f"Build mastery in {repeated_weak_concept.replace('_', ' ')}"
        reason = (
            f"{repeated_weak_concept.replace('_', ' ').capitalize()} was missed again after "
            "already being a weak concept, so Kinara is prioritizing it before moving on."
        )
    elif updated_memory.weak_concepts:
        weakest = updated_memory.weak_concepts[0]
        topic = last_topic
        objective = f"Strengthen {weakest.replace('_', ' ')}"
        reason = (
            f"Recent sessions show {updated_memory.learning_trend} performance, and "
            f"{weakest.replace('_', ' ')} remains a weak concept, so Kinara kept the focus there."
        )
    else:
        topic = last_topic
        objective = f"Progress further in {last_topic}"
        reason = (
            f"Performance has been {updated_memory.learning_trend} with no outstanding weak "
            f"concepts, so Kinara is increasing the challenge to {difficulty}."
        )

    return NextExperience(topic=topic, difficulty=difficulty, objective=objective, reason=reason)
