"""Firestore persistence for Zunara."""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from src.models.child import Child
from src.models.learning_memory import LearningMemory
from src.models.session import LearningSession
from src.models.user import User

logger = logging.getLogger(__name__)


class FirestoreUnavailableError(RuntimeError):
    """Raised when a Firestore operation fails."""


class FirestoreService:
    def __init__(self, db, uid: str):
        if not uid:
            raise ValueError("FirestoreService requires a verified uid")
        self._db = db
        self._uid = uid

    def _user_ref(self):
        return self._db.collection("users").document(self._uid)

    def _child_ref(self, child_id: str):
        return self._user_ref().collection("children").document(child_id)

    def _memory_ref(self, child_id: str):
        return self._child_ref(child_id).collection("learningMemory").document("current")

    def _session_ref(self, child_id: str, session_id: str):
        return self._child_ref(child_id).collection("sessions").document(session_id)

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
            logger.exception("Could not load or create account: %s", exc)
            raise FirestoreUnavailableError("Could not load or create your account.") from exc

    def get_user(self) -> User | None:
        try:
            snap = self._user_ref().get()
            return User.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Could not load account: %s", exc)
            raise FirestoreUnavailableError("Could not load your account.") from exc

    def create_child(self, name: str, educational_level: str, preferred_learning_style: str | None) -> Child:
        try:
            child_id = str(uuid.uuid4())
            child = Child(child_id=child_id, name=name, educational_level=educational_level, preferred_learning_style=preferred_learning_style)
            self._child_ref(child_id).set(child.to_firestore())
            self._memory_ref(child_id).set(LearningMemory().to_firestore())
            return child
        except Exception as exc:
            logger.exception("Could not create child: %s", exc)
            raise FirestoreUnavailableError("Could not create the child profile.") from exc

    def list_children(self) -> list[Child]:
        try:
            docs = self._user_ref().collection("children").stream()
            return [Child.from_firestore(d.to_dict()) for d in docs]
        except Exception as exc:
            logger.exception("Could not load children: %s", exc)
            raise FirestoreUnavailableError("Could not load children.") from exc

    def get_child(self, child_id: str) -> Child | None:
        try:
            snap = self._child_ref(child_id).get()
            return Child.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Could not load child: %s", exc)
            raise FirestoreUnavailableError("Could not load child profile.") from exc

    def update_child_xp_streak(self, child_id: str, xp: int, streak: int) -> None:
        try:
            self._child_ref(child_id).update({"xp": xp, "streak": streak, "updatedAt": datetime.now(timezone.utc)})
        except Exception as exc:
            logger.exception("Could not update progress: %s", exc)
            raise FirestoreUnavailableError("Could not update child progress.") from exc

    def get_learning_memory(self, child_id: str) -> LearningMemory:
        try:
            snap = self._memory_ref(child_id).get()
            return LearningMemory.from_firestore(snap.to_dict() if snap.exists else None)
        except Exception as exc:
            logger.exception("Could not load memory: %s", exc)
            raise FirestoreUnavailableError("Could not load Learning Memory.") from exc

    def save_learning_memory(self, child_id: str, memory: LearningMemory) -> None:
        try:
            self._memory_ref(child_id).set(memory.to_firestore())
        except Exception as exc:
            logger.exception("Could not save memory: %s", exc)
            raise FirestoreUnavailableError("Could not save Learning Memory.") from exc

    def create_session(self, child_id: str, session: LearningSession) -> None:
        try:
            self._session_ref(child_id, session.session_id).set(session.to_firestore())
        except Exception as exc:
            logger.exception("Could not start session: %s", exc)
            raise FirestoreUnavailableError("Could not start the learning session.") from exc

    def get_session(self, child_id: str, session_id: str) -> LearningSession | None:
        try:
            snap = self._session_ref(child_id, session_id).get()
            return LearningSession.from_firestore(snap.to_dict()) if snap.exists else None
        except Exception as exc:
            logger.exception("Could not load session: %s", exc)
            raise FirestoreUnavailableError("Could not load the learning session.") from exc

    def get_active_session(self, child_id: str) -> LearningSession | None:
        """Return the newest generated-but-not-completed session for a child."""
        try:
            docs = self._child_ref(child_id).collection("sessions").stream()
            sessions = [LearningSession.from_firestore(d.to_dict()) for d in docs]
            active = [s for s in sessions if not s.completed]
            if not active:
                return None
            return max(active, key=lambda s: s.started_at)
        except Exception as exc:
            logger.exception("Could not load active session: %s", exc)
            raise FirestoreUnavailableError("Could not load the current learning activity.") from exc

    def complete_session(self, child_id: str, session: LearningSession) -> None:
        try:
            self._session_ref(child_id, session.session_id).set(session.to_firestore())
        except Exception as exc:
            logger.exception("Could not save results: %s", exc)
            raise FirestoreUnavailableError("Could not save your results.") from exc

    def _fetch_completed_sessions(self, child_id: str, limit: int, error_message: str) -> list[LearningSession]:
        try:
            docs = self._child_ref(child_id).collection("sessions").order_by("completedAt", direction="DESCENDING").stream()
            sessions = [LearningSession.from_firestore(d.to_dict()) for d in docs]
        except Exception as exc:
            logger.exception("Could not load sessions: %s", exc)
            raise FirestoreUnavailableError(error_message) from exc
        return [s for s in sessions if s.completed][:limit]

    def list_recent_sessions(self, child_id: str, limit: int = 3) -> list[LearningSession]:
        return self._fetch_completed_sessions(child_id, limit, "Could not load recent sessions.")

    def list_session_history(self, child_id: str, limit: int = 100) -> list[LearningSession]:
        return self._fetch_completed_sessions(child_id, limit, "Could not load exam history.")

    # -- Parent ↔ Learner account linking ---------------------------------

    def create_link_code(self, child_id: str) -> str:
        """Create a short-lived one-time code for this parent's child."""
        try:
            child = self.get_child(child_id)
            if child is None:
                raise ValueError("Child profile not found.")
            code = secrets.token_hex(4).upper()
            now = datetime.now(timezone.utc)
            self._db.collection("linkCodes").document(code).set({
                "parentUid": self._uid,
                "childId": child_id,
                "childName": child.name,
                "createdAt": now,
                "expiresAt": now + timedelta(minutes=30),
                "claimedBy": None,
            })
            return code
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Could not create link code: %s", exc)
            raise FirestoreUnavailableError("Could not create a linking code.") from exc

    def claim_link_code(self, code: str) -> User:
        """Claim a parent-generated code for the currently signed-in learner."""
        try:
            if not code.strip():
                raise ValueError("Enter the linking code.")
            ref = self._db.collection("linkCodes").document(code.strip().upper())
            snap = ref.get()
            if not snap.exists:
                raise ValueError("Invalid linking code.")
            data = snap.to_dict()
            expires_at = data.get("expiresAt")
            if expires_at and expires_at < datetime.now(timezone.utc):
                raise ValueError("This linking code has expired. Ask the parent for a new code.")
            if data.get("claimedBy"):
                raise ValueError("This linking code has already been used.")
            if data.get("parentUid") == self._uid:
                raise ValueError("A parent account cannot link to itself.")
            current = self.get_user()
            if current is None or current.role != "learner":
                raise ValueError("Only a learner account can claim a linking code.")

            parent_ref = self._db.collection("users").document(data["parentUid"])
            parent_snap = parent_ref.get()
            if not parent_snap.exists:
                raise ValueError("The parent account could not be found.")
            parent = User.from_firestore(parent_snap.to_dict())
            child_id = data["childId"]
            child_snap = parent_ref.collection("children").document(child_id).get()
            if not child_snap.exists:
                raise ValueError("The child profile no longer exists.")

            self._user_ref().update({"linkedParentUid": parent.uid, "linkedChildId": child_id})
            parent_ref.update({
                "linkedLearnerUid": self._uid,
                "linkedLearnerEmail": current.email,
                "linkedChildId": child_id,
            })
            ref.update({"claimedBy": self._uid, "claimedAt": datetime.now(timezone.utc)})
            return User.from_firestore({**current.to_firestore(), "linkedParentUid": parent.uid, "linkedChildId": child_id})
        except ValueError:
            raise
        except Exception as exc:
            logger.exception("Could not claim link code: %s", exc)
            raise FirestoreUnavailableError("Could not link the learner account.") from exc
