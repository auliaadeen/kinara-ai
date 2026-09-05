"""Learner workspace.

Learners do not manage child profiles. A learner must be linked to a child
profile before learning data can be shown; the linking workflow is intentionally
kept separate so learner access cannot accidentally expose another user's data.
"""
from __future__ import annotations

import streamlit as st

from src.config import Settings
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme


def render_learner_dashboard(settings: Settings, db) -> None:
    """Render the learner-facing workspace without parent-only controls."""
    theme.hero(
        "Zunara AI · Learner view",
        "Your learning journey",
        "Zunara adapts each activity to your progress and learning pace.",
    )

    fs = FirestoreService(db, st.session_state.uid)
    try:
        children = fs.list_children()
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    # Current data model scopes children beneath the signed-in user's uid.
    # Until an explicit Parent → Learner linking workflow exists, do not
    # silently create or duplicate a child profile for a learner.
    if not children:
        with st.container(border=True):
            st.markdown(
                "##### :material/link: Your learning profile is not linked yet",
                text_alignment="center",
            )
            st.caption(
                "Ask your parent or teacher to connect your Zunara account to your learner profile.",
                text_alignment="center",
            )
        return

    # Temporary compatibility path for existing learner accounts that already
    # have a child document under their uid. This does not create new data.
    child = children[0]
    try:
        memory = fs.get_learning_memory(child.child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    theme.section_title("auto_awesome", "Recommended next")
    with st.container(border=True):
        st.write(f"Continue learning **{child.name}**'s current topic.")
        st.caption("Your recommended activity will use your saved learning progress.")
        if st.button("Start Learning", type="primary", icon=":material/play_arrow:", width="stretch"):
            st.session_state.selected_child_id = child.child_id
            st.session_state.view = "session"
            st.rerun()

    theme.section_title("bar_chart", "My progress")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("XP", memory.total_xp)
        col2.metric("Streak", memory.streak)
        mastery = round(sum(memory.mastery_map.values()) / len(memory.mastery_map), 1) if memory.mastery_map else 0
        col3.metric("Mastery", f"{mastery}%")
