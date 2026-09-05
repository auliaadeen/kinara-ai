"""users/{uid} account model."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import Role


class User(BaseModel):
    uid: str
    email: str
    role: Role
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    linked_parent_uid: str | None = None
    linked_child_id: str | None = None
    linked_learner_uid: str | None = None
    linked_learner_email: str | None = None

    def to_firestore(self) -> dict:
        return {
            "uid": self.uid,
            "email": self.email,
            "role": self.role,
            "createdAt": self.created_at,
            "linkedParentUid": self.linked_parent_uid,
            "linkedChildId": self.linked_child_id,
            "linkedLearnerUid": self.linked_learner_uid,
            "linkedLearnerEmail": self.linked_learner_email,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "User":
        return cls(
            uid=data["uid"],
            email=data["email"],
            role=data["role"],
            created_at=data.get("createdAt") or datetime.now(timezone.utc),
            linked_parent_uid=data.get("linkedParentUid"),
            linked_child_id=data.get("linkedChildId"),
            linked_learner_uid=data.get("linkedLearnerUid"),
            linked_learner_email=data.get("linkedLearnerEmail"),
        )
