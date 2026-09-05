"""Shared session-launch helper (FSD.md #3.4, UI-002).

Both the manual "Generate" form and the "Continue Learning" CTAs
(dashboard and Session Success / Results) funnel through this single
function so there's exactly one place that turns a
topic/difficulty into an active session — "Continue Learning" reuses the
already-computed Recommended Next output, it does not invent a second
recommendation or call Gemini to decide difficulty/topic (AI_SPEC.md §0).
"""
from __future__ import annotations

import streamlit as st

from src.config import Settings
from src.models.common import Difficulty
from src.services import session_service
from src.services.ai_engine import AIGenerationError
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError


def launch_session(
    settings: Settings,
    fs: FirestoreService,
    child_id: str,
    topic: str,
    difficulty: Difficulty | None,
) -> bool:
    """Generates the next session and, on success, points session_state at
    it. Returns True on success (caller should st.rerun()); False on
    failure (error already shown via st.error, view unchanged)."""
    with st.spinner("Zunara is preparing the activity..."):
        try:
            session = session_service.generate_learning_experience(
                settings, fs, child_id, topic, difficulty
            )
        except session_service.ChildNotFoundError as exc:
            st.error(str(exc))
            return False
        except FirestoreUnavailableError as exc:
            st.error(str(exc))
            return False
        except AIGenerationError as exc:
            st.error(str(exc))
            return False

    st.session_state.current_session = session
    st.session_state.view = "session"
    return True
