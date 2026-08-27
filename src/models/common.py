"""Shared literal/enum-like types used across models (DATA_MODEL.md, FSD.md #8)."""
from __future__ import annotations

from typing import Literal

Role = Literal["parent", "learner"]

Difficulty = Literal["easy", "medium", "hard"]
DIFFICULTY_ORDER: list[Difficulty] = ["easy", "medium", "hard"]

LearningTrend = Literal["improving", "declining", "stable"]

QuestionType = Literal["multiple_choice"]


def step_difficulty(current: Difficulty, steps: int) -> Difficulty:
    """Move difficulty up/down the fixed scale, clamped at both ends."""
    idx = DIFFICULTY_ORDER.index(current)
    new_idx = max(0, min(len(DIFFICULTY_ORDER) - 1, idx + steps))
    return DIFFICULTY_ORDER[new_idx]
