"""Learner workspace.

Learners do not manage child profiles. A learner must be linked to a child
profile before learning data can be shown; the linking workflow is intentionally
kept separate so learner access cannot accidentally expose another user's data.
"""
from __future__ import annotations

import streamlit as st

from src.config import Settings
from src.services import exam_history, gamification
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme


def _get_learner_child(fs: FirestoreService):
    """Return the learner's existing child profile, if one exists.

    The current MVP data model stores child profiles under the signed-in user.
    This is intentionally read-only here until Parent → Learner linking is
    implemented as an explicit, secure workflow.
    """
    children = fs.list_children()
    return children[0] if children else None


def render_learner_dashboard(settings: Settings, db) -> None:
    """Render the learner-facing workspace without parent-only controls."""
    fs = FirestoreService(db, st.session_state.uid)
    try:
        child = _get_learner_child(fs)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    if not child:
        theme.hero(
            "Zunara AI · Learner view",
            "Your learning journey",
            "Zunara adapts each activity to your progress and learning pace.",
        )
        with st.container(border=True):
            st.markdown("##### :material/link: Your learning profile is not linked yet", text_alignment="center")
            st.caption(
                "Ask your parent or teacher to connect your Zunara account to your learner profile.",
                text_alignment="center",
            )
        return

    try:
        memory = fs.get_learning_memory(child.child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    theme.hero("Zunara AI · Learner view", f"Hi, {child.name}!", child.educational_level)

    theme.section_title("auto_awesome", "Recommended next")
    with st.container(border=True):
        if memory.recent_topics:
            topic = memory.recent_topics[0]
            st.markdown(f"#### {topic}")
            st.caption(f"Difficulty: {memory.recommended_difficulty}")
            st.write("Continue with an activity adapted to your saved learning progress.")
        else:
            topic = ""
            st.write("Your first learning activity will appear here once your profile is ready.")

    theme.section_title("bar_chart", "My progress")
    with st.container(border=True):
        level_number, level_name = gamification.compute_level(memory.total_xp)
        mastery = round(sum(memory.mastery_map.values()) / len(memory.mastery_map), 1) if memory.mastery_map else 0
        cols = st.columns(4, gap="small")
        cols[0].metric("XP", memory.total_xp)
        cols[1].metric("Level", f"{level_number} — {level_name}")
        cols[2].metric("Streak", memory.streak)
        cols[3].metric("Mastery", f"{mastery}%")

    if memory.recent_topics:
        theme.section_title("psychology", "What Zunara remembers")
        with st.container(border=True):
            st.caption(f"Learning trend: {memory.learning_trend}")
            if memory.weak_concepts:
                st.write("**Needs practice:** " + ", ".join(c.replace("_", " ") for c in memory.weak_concepts))
            if memory.strong_concepts:
                st.write("**Doing well:** " + ", ".join(c.replace("_", " ") for c in memory.strong_concepts))


def render_learner_history(db) -> None:
    """Render history scoped to the learner's own existing child profile."""
    fs = FirestoreService(db, st.session_state.uid)
    try:
        child = _get_learner_child(fs)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    theme.hero("Zunara AI · History", "My learning history", "Review your completed learning sessions.")
    if not child:
        st.info("Your learner profile is not linked yet.")
        return

    try:
        sessions = fs.list_session_history(child.child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    if not sessions:
        st.caption("No completed sessions yet.")
        return

    rows = exam_history.build_history_rows(sessions)
    theme.section_title("history", "Completed sessions")
    with st.container(border=True):
        st.dataframe(
            [
                {
                    "Date": row.completed_at.strftime("%Y-%m-%d %H:%M") if row.completed_at else "—",
                    "Topic": row.topic,
                    "Score": f"{row.score:.0f}%",
                    "Grade": f"{row.grade_letter} — {row.grade_label}",
                    "Trend": row.trend_label,
                    "XP earned": row.xp_earned,
                    "Status": row.status,
                }
                for row in rows
            ],
            width="stretch",
        )
