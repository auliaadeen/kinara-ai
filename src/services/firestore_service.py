"""Firestore persistence (DATA_MODEL.md, SECURITY.md, ARCHITECTURE.md #3).

Every method takes a verified `uid` and only ever reads/writes under
`users/{uid}/...`. There is no method that accepts a caller-supplied uid for
someone else's data — cross-user access is structurally impossible through
this class, not just policy (SECURITY-001).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from src.models.child import Child
from src.models.learning_memory import LearningMemory
from src.models.session import LearningSession
from src.models.user import User

logger = logging.getLogger(__name__)


class FirestoreUnavailableError(RuntimeError):
    """Raised when a Firestore operation fails (FSD.md #12 — never pretend it saved)."""


class FirestoreService:
    def __init__(self, db, uid: str):
        if not uid:
            raise ValueError("FirestoreService requires a verified uid")
        self._db = db
        self._uid = uid

    # -- paths, always rooted at this instance's uid --------------------

    def _user_ref(self):
        return self._db.collection("users").document(self._uid)

    def _child_ref(self, child_id: str):
        return self._user_ref().collection("children").document(child_id)

    def _memory_ref(self, child_id: str):
        return self._child_ref(child_id).collection("learningMemory").document("current")

    def _session_ref(self, child_id: str, session_id: str):
        return self._child_ref(child_id).collection("sessions").document(session_id)

    # -- user -------------------------------------------------------------

    def ensure_user(self, email: str, role: str) -> User:
        try:
            ref = self._user_ref()
            snap = ref.get()
            if snap.exists:
                return User.from_firestore(snap.to_dict())
            user = User(uid=self._uid, email=email, role=role)
            ref.set(user.to_firestore())
            return user
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load or create your account.", exc)
            raise FirestoreUnavailableError("Could not load or create your account.") from exc

    def get_user(self) -> User | None:
        try:
            snap = self._user_ref().get()
            return User.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load your account.", exc)
            raise FirestoreUnavailableError("Could not load your account.") from exc

    # -- children -----------------------------------------------------------

    def create_child(
        self, name: str, educational_level: str, preferred_learning_style: str | None
    ) -> Child:
        try:
            child_id = str(uuid.uuid4())
            child = Child(
                child_id=child_id,
                name=name,
                educational_level=educational_level,
                preferred_learning_style=preferred_learning_style,
            )
            self._child_ref(child_id).set(child.to_firestore())
            self._memory_ref(child_id).set(LearningMemory().to_firestore())
            return child
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not create the child profile.", exc)
            raise FirestoreUnavailableError("Could not create the child profile.") from exc

    def list_children(self) -> list[Child]:
        try:
            docs = self._user_ref().collection("children").stream()
            return [Child.from_firestore(d.to_dict()) for d in docs]
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load children.", exc)
            raise FirestoreUnavailableError("Could not load children.") from exc

    def get_child(self, child_id: str) -> Child | None:
        try:
            snap = self._child_ref(child_id).get()
            return Child.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load child profile.", exc)
            raise FirestoreUnavailableError("Could not load child profile.") from exc

    def update_child_xp_streak(self, child_id: str, xp: int, streak: int) -> None:
        try:
            self._child_ref(child_id).update(
                {"xp": xp, "streak": streak, "updatedAt": datetime.now(timezone.utc)}
            )
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not update child progress.", exc)
            raise FirestoreUnavailableError("Could not update child progress.") from exc

    # -- learning memory ------------------------------------------------------

    def get_learning_memory(self, child_id: str) -> LearningMemory:
        try:
            snap = self._memory_ref(child_id).get()
            return LearningMemory.from_firestore(snap.to_dict() if snap.exists else None)
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load Learning Memory.", exc)
            raise FirestoreUnavailableError("Could not load Learning Memory.") from exc

    def save_learning_memory(self, child_id: str, memory: LearningMemory) -> None:
        try:
            self._memory_ref(child_id).set(memory.to_firestore())
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not save Learning Memory.", exc)
            raise FirestoreUnavailableError("Could not save Learning Memory.") from exc

    # -- sessions -----------------------------------------------------------

    def create_session(self, child_id: str, session: LearningSession) -> None:
        try:
            self._session_ref(child_id, session.session_id).set(session.to_firestore())
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not start the learning session.", exc)
            raise FirestoreUnavailableError("Could not start the learning session.") from exc

    def get_session(self, child_id: str, session_id: str) -> LearningSession | None:
        try:
            snap = self._session_ref(child_id, session_id).get()
            return LearningSession.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load the learning session.", exc)
            raise FirestoreUnavailableError("Could not load the learning session.") from exc

    def complete_session(self, child_id: str, session: LearningSession) -> None:
        try:
            self._session_ref(child_id, session.session_id).set(session.to_firestore())
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not save your results.", exc)
            raise FirestoreUnavailableError("Could not save your results.") from exc

    def list_recent_sessions(self, child_id: str, limit: int = 3) -> list[LearningSession]:
        """Combining an equality filter (completed == True) with order_by on a
        different field (completedAt) needs a Firestore composite index that
        doesn't exist by default — Firestore raises FAILED_PRECONDITION for
        that query shape even against an empty collection, before any data
        is inspected. Ordering by a single field only avoids that entirely
        (Firestore auto-indexes every field on its own), and the
        completed-only filtering + limit happen here in Python instead."""
        try:
            query = (
                self._child_ref(child_id)
                .collection("sessions")
                .order_by("completedAt", direction="DESCENDING")
            )
            docs = query.stream()
            sessions = [LearningSession.from_firestore(d.to_dict()) for d in docs]
        except Exception as exc:
            logger.exception("Firestore op failed (%s): %s", "Could not load recent sessions.", exc)
            raise FirestoreUnavailableError("Could not load recent sessions.") from exc
        return [s for s in sessions if s.completed][:limit]
