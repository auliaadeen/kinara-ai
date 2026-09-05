"""Learner dashboard and history views."""
from __future__ import annotations

import streamlit as st

from src.services import exam_history, gamification
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme
from src.ui.session_launch import launch_session


def _get_linked_child(fs: FirestoreService):
    user = fs.get_user()
    if not user or user.role != "learner" or not user.linked_parent_uid or not user.linked_child_id:
        return None, None
    parent_fs = FirestoreService(fs._db, user.linked_parent_uid)
    child = parent_fs.get_child(user.linked_child_id)
    return parent_fs, child


def _progress_section(memory) -> None:
    theme.section_title("bar_chart", "My progress")
    level_number, level_name = gamification.compute_level(memory.total_xp)
    avg_mastery = round(sum(memory.mastery_map.values()) / len(memory.mastery_map), 1) if memory.mastery_map else 0
    cols = st.columns(4, gap="small")
    metrics = [("XP", memory.total_xp), ("Level", f"{level_number} — {level_name}"), ("Streak", memory.streak), ("Mastery", f"{avg_mastery}%")]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown('<div class="zunara-progress-metric">', unsafe_allow_html=True)
            st.caption(label)
            st.markdown(f'<div class="zunara-progress-value">{value}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"Learning trend: {memory.learning_trend}")


def render_learner_dashboard(settings, db) -> None:
    fs = FirestoreService(db, st.session_state.uid)
    try:
        parent_fs, child = _get_linked_child(fs)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    if not parent_fs or not child:
        theme.hero("Zunara AI · Learner view", "Your learning space", "Connect your learner account to a parent profile to begin.")
        with st.container(border=True):
            st.write("Your learning profile is not linked yet.")
            st.caption("Open Settings → Parent Connection and enter the one-time code from your parent.")
        return

    try:
        memory = parent_fs.get_learning_memory(child.child_id)
        active_session = parent_fs.get_active_session(child.child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    theme.hero("Zunara AI · Learner view", f"Hi, {child.name}!", child.educational_level)

    if active_session:
        theme.section_title("play_circle", "Ready to learn")
        with st.container(key=theme.CTA_KEY, border=True):
            theme.cta_eyebrow("bolt", "Activity from your parent")
            st.markdown(f"#### {active_session.title}")
            st.caption(f"{len(active_session.questions)} questions · Difficulty: {active_session.difficulty}")
            st.write(active_session.objective)
            if st.button("Start Learning", type="primary", icon=":material/play_arrow:", width="stretch"):
                st.session_state.selected_child_id = child.child_id
                st.session_state.current_session = active_session
                st.session_state.view = "session"
                st.rerun()
    else:
        theme.section_title("check_circle", "All caught up")
        st.caption("No pending activity right now. Ask your parent to set a new learning activity.")

    _progress_section(memory)

    if memory.recent_topics:
        theme.section_title("auto_awesome", "What Zunara is working on")
        with st.container(border=True):
            st.write(", ".join(memory.recent_topics[:3]))


def render_learner_history(db) -> None:
    fs = FirestoreService(db, st.session_state.uid)
    try:
        parent_fs, child = _get_linked_child(fs)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return
    theme.hero("Zunara AI · History", "My learning history", "Your completed learning sessions are shared with your parent.")
    if not parent_fs or not child:
        st.info("Connect your learner account to a parent profile first.")
        return
    try:
        sessions = parent_fs.list_session_history(child.child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return
    if not sessions:
        st.caption("No completed sessions yet.")
        return
    rows = exam_history.build_history_rows(sessions)
    st.dataframe([
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
    ], width="stretch")
