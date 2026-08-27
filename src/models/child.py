"""users/{uid}/children/{childId} (DATA_MODEL.md)."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Child(BaseModel):
    child_id: str
    name: str = Field(min_length=1, max_length=80)
    educational_level: str = Field(min_length=1, max_length=40)
    preferred_learning_style: str | None = None
    xp: int = 0
    streak: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_firestore(self) -> dict:
        return {
            "childId": self.child_id,
            "name": self.name,
            "educationalLevel": self.educational_level,
            "preferredLearningStyle": self.preferred_learning_style,
            "xp": self.xp,
            "streak": self.streak,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "Child":
        return cls(
            child_id=data["childId"],
            name=data["name"],
            educational_level=data["educationalLevel"],
            preferred_learning_style=data.get("preferredLearningStyle"),
            xp=data.get("xp", 0),
            streak=data.get("streak", 0),
            created_at=data.get("createdAt") or datetime.now(timezone.utc),
            updated_at=data.get("updatedAt") or datetime.now(timezone.utc),
        )
