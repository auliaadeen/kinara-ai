"""users/{uid}/children/{childId}/learningMemory/current (DATA_MODEL.md, FSD.md #7).

This is the core differentiator (PRD.md #5): accumulated, measurable learning
evidence that must influence future generation (AI_RULES Rule 7).
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import Difficulty, LearningTrend


class LearningMemory(BaseModel):
    mastery_map: dict[str, float] = Field(default_factory=dict)  # concept_slug -> 0..100
    # concept_slug -> recent correct/incorrect outcomes (oldest first, capped
    # window). Source of truth for mastery_map — history-aware progression
    # needs more than a single scalar per concept (src/services/gamification.py).
    concept_history: dict[str, list[bool]] = Field(default_factory=dict)
    weak_concepts: list[str] = Field(default_factory=list)
    strong_concepts: list[str] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    recommended_difficulty: Difficulty = "easy"
    learning_trend: LearningTrend = "stable"
    total_xp: int = 0
    streak: int = 0
    last_session_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_history(self) -> bool:
        return self.last_session_at is not None

    def to_firestore(self) -> dict:
        return {
            "masteryMap": self.mastery_map,
            "conceptHistory": self.concept_history,
            "weakConcepts": self.weak_concepts,
            "strongConcepts": self.strong_concepts,
            "recentTopics": self.recent_topics,
            "recommendedDifficulty": self.recommended_difficulty,
            "learningTrend": self.learning_trend,
            "totalXP": self.total_xp,
            "streak": self.streak,
            "lastSessionAt": self.last_session_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_firestore(cls, data: dict | None) -> "LearningMemory":
        if not data:
            return cls()
        return cls(
            mastery_map=data.get("masteryMap", {}),
            concept_history=data.get("conceptHistory", {}),
            weak_concepts=data.get("weakConcepts", []),
            strong_concepts=data.get("strongConcepts", []),
            recent_topics=data.get("recentTopics", []),
            recommended_difficulty=data.get("recommendedDifficulty", "easy"),
            learning_trend=data.get("learningTrend", "stable"),
            total_xp=data.get("totalXP", 0),
            streak=data.get("streak", 0),
            last_session_at=data.get("lastSessionAt"),
            updated_at=data.get("updatedAt") or datetime.now(timezone.utc),
        )
