"""Gemini structured-output schemas (AI_SPEC.md #2, #6).

Every Gemini response is validated against these before the app trusts it.
Gemini generates worksheet CONTENT only — score, XP, mastery, difficulty
progression and the "next experience" reason stay in Python
(ARCHITECTURE.md #3, AI_SPEC.md #5).
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .common import Difficulty


class GeneratedQuestion(BaseModel):
    id: str
    prompt: str = Field(min_length=1)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_answer_index: int = Field(ge=0)
    concept: str = Field(min_length=1)

    @field_validator("correct_answer_index")
    @classmethod
    def _index_in_range(cls, v: int, info) -> int:
        options = info.data.get("options")
        if options is not None and v >= len(options):
            raise ValueError("correct_answer_index out of range for options")
        return v


class WorksheetResponse(BaseModel):
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    difficulty: Difficulty
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=10)
