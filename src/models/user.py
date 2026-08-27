"""users/{uid} (DATA_MODEL.md)."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import Role


class User(BaseModel):
    uid: str
    email: str
    role: Role
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_firestore(self) -> dict:
        return {
            "uid": self.uid,
            "email": self.email,
            "role": self.role,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "User":
        return cls(
            uid=data["uid"],
            email=data["email"],
            role=data["role"],
            created_at=data.get("createdAt") or datetime.now(timezone.utc),
        )
