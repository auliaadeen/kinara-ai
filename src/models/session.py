"""users/{uid}/children/{childId}/sessions/{sessionId} (DATA_MODEL.md, FSD.md #4)."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import Difficulty


class QuestionRecord(BaseModel):
    id: str
    prompt: str
    options: list[str]
    concept: str  # normalized concept slug this question tests


class LearningSession(BaseModel):
    session_id: str
    topic: str
    difficulty: Difficulty
    title: str
    objective: str
    questions: list[QuestionRecord]
    answer_key: dict[str, int]  # question id -> correct option index (server-side only)
    answers: dict[str, int] = Field(default_factory=dict)  # question id -> chosen option index
    score: float | None = None
    incorrect_concepts: list[str] = Field(default_factory=list)
    time_spent_seconds: int | None = None
    completed: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_firestore(self) -> dict:
        return {
            "sessionId": self.session_id,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "title": self.title,
            "objective": self.objective,
            "questions": [q.model_dump() for q in self.questions],
            "answerKey": self.answer_key,
            "answers": self.answers,
            "score": self.score,
            "incorrectConcepts": self.incorrect_concepts,
            "timeSpentSeconds": self.time_spent_seconds,
            "completed": self.completed,
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "LearningSession":
        return cls(
            session_id=data["sessionId"],
            topic=data["topic"],
            difficulty=data["difficulty"],
            title=data.get("title", ""),
            objective=data.get("objective", ""),
            questions=[QuestionRecord(**q) for q in data.get("questions", [])],
            answer_key=data.get("answerKey", {}),
            answers=data.get("answers", {}),
            score=data.get("score"),
            incorrect_concepts=data.get("incorrectConcepts", []),
            time_spent_seconds=data.get("timeSpentSeconds"),
            completed=data.get("completed", False),
            started_at=data.get("startedAt") or datetime.now(timezone.utc),
            completed_at=data.get("completedAt"),
        )
