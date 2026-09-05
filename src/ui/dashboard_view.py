"""Parent dashboard and exam history views."""
from __future__ import annotations

from datetime import datetime, timezone
import streamlit as st

from src.config import Settings
from src.models.common import DIFFICULTY_ORDER
from src.services import adaptive_engine, exam_history, gamification
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme
from src.ui.session_launch import launch_session


def _create_child_form(fs: FirestoreService) -> None:
    with st.expander("Add a child", icon=":material/person_add:", expanded=False):
        with st.form("create_child_form"):
            name = st.text_input("Name")
            level = st.text_input("Educational level (e.g. Grade 2)")
            style = st.text_input("Preferred learning style (optional)")
            submitted = st.form_submit_button("Create child", icon=":material/check:")
        if submitted:
            if not name.strip() or not level.strip():
                st.error("Name and educational level are required.")
                return
            try:
                fs.create_child(name.strip(), level.strip(), style.strip() or None)
            except FirestoreUnavailableError as exc:
                st.error(str(exc))
            else:
                st.toast(f"{name} added.", icon=":material/celebration:")
                st.rerun()


def _generate_form(settings: Settings, fs: FirestoreService, child_id: str, default_topic: str, default_difficulty: str) -> None:
    theme.section_title("edit_note", "Generate a learning activity")
    with st.container(border=True):
        with st.form("generate_form"):
            topic = st.text_input("Topic", value=default_topic)
            options = ["(use recommended)"] + list(DIFFICULTY_ORDER)
            difficulty = st.selectbox("Difficulty (optional override)", options=options, index=options.index(default_difficulty) if default_difficulty in options else 0)
            submitted = st.form_submit_button("Generate", icon=":material/auto_awesome:")
        if submitted:
            if not topic.strip():
                st.error("Topic is required.")
                return
            override = None if difficulty == "(use recommended)" else difficulty
            if launch_session(settings, fs, child_id, topic.strip(), override):
                st.rerun()


def _memory_section(memory) -> None:
    theme.section_title("psychology", "What Zunara remembers")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("Weak concepts")
            if memory.weak_concepts:
                with st.container(horizontal=True):
                    for concept in memory.weak_concepts:
                        st.badge(concept.replace("_", " "), icon=":material/trending_down:", color="orange")
            else:
                st.caption("None yet")
        with col2:
            st.caption("Strong concepts")
            if memory.strong_concepts:
                with st.container(horizontal=True):
                    for concept in memory.strong_concepts:
                        st.badge(concept.replace("_", " "), icon=":material/trending_up:", color="green")
            else:
                st.caption("None yet")
        with col3:
            st.caption("Recent topics")
            if memory.recent_topics:
                with st.container(horizontal=True):
                    for topic in memory.recent_topics:
                        st.badge(topic, icon=":material/history:", color="gray")
            else:
                st.caption("None yet")


def _recommended_next_section(settings: Settings, fs: FirestoreService, child_id: str, memory) -> tuple[str, str]:
    theme.section_title("auto_awesome", "Recommended next")
    default_topic = ""
    default_difficulty = memory.recommended_difficulty
    if memory.has_history and memory.recent_topics:
        rec = adaptive_engine.build_next_experience(updated_memory=memory, last_topic=memory.recent_topics[0], repeated_weak_concept=None)
        with st.container(key=theme.CTA_KEY, border=True):
            theme.cta_eyebrow("bolt", "Zunara's pick for today")
            st.markdown(f"#### {rec.topic}")
            st.caption(f"Difficulty: {rec.difficulty}")
            st.write(rec.reason)
            if st.button("Continue Learning", type="primary", icon=":material/play_arrow:", width="stretch"):
                if launch_session(settings, fs, child_id, rec.topic, rec.difficulty):
                    st.rerun()
        default_topic = rec.topic
    else:
        with st.container(border=True):
            st.write("No learning history yet — generate the first activity below.")
    return default_topic, default_difficulty


def _progress_section(memory) -> None:
    theme.section_title("bar_chart", "Progress")
    level_number, level_name = gamification.compute_level(memory.total_xp)
    status = gamification.strike_status(memory.streak, memory.last_session_at, datetime.now(timezone.utc))
    avg_mastery = round(sum(memory.mastery_map.values()) / len(memory.mastery_map), 1) if memory.mastery_map else 0

    metrics = [
        ("XP", str(memory.total_xp)),
        ("Zunara level", f"{level_number} — {level_name}"),
        ("Streak", str(memory.streak)),
        ("Mastery", f"{avg_mastery}%"),
        ("Trend", memory.learning_trend),
    ]

    # Each metric is a real Streamlit bordered container. The previous
    # implementation opened an HTML <div> with st.markdown and then emitted
    # Streamlit widgets outside that DOM node, so the values rendered below
    # the visual cards. Keeping the widgets inside st.container() makes the
    # card boundary contain both label and value reliably.
    cols = st.columns([0.9, 1.55, 0.9, 1.0, 1.05], gap="small")
    for col, (label, value) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"**{value}**")
    st.caption(status)


def _history_table(fs: FirestoreService, child_id: str) -> None:
    try:
        sessions = fs.list_session_history(child_id)
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


def render_dashboard(settings: Settings, db) -> None:
    fs = FirestoreService(db, st.session_state.uid)
    try:
        children = fs.list_children()
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return
    _create_child_form(fs)
    if not children:
        with st.container(border=True):
            st.markdown("##### :material/family_restroom: Create a child profile to get started", text_alignment="center")
            st.caption("Zunara adapts every learning session to your child's pace once a profile exists.", text_alignment="center")
        return
    names = {c.child_id: c.name for c in children}
    default_id = st.session_state.get("selected_child_id") or children[0].child_id
    if default_id not in names:
        default_id = children[0].child_id
    child_id = st.selectbox("Child", options=list(names.keys()), format_func=lambda cid: names[cid], index=list(names.keys()).index(default_id))
    st.session_state.selected_child_id = child_id
    try:
        child = fs.get_child(child_id)
        memory = fs.get_learning_memory(child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return
    theme.hero("Zunara AI · Parent view", f"How {child.name} is doing", child.educational_level)
    _memory_section(memory)
    default_topic, default_difficulty = _recommended_next_section(settings, fs, child_id, memory)
    _progress_section(memory)
    _generate_form(settings, fs, child_id, default_topic, default_difficulty)


def render_history(db) -> None:
    fs = FirestoreService(db, st.session_state.uid)
    theme.hero("Zunara AI · History", "Learning history", "Review your child's completed learning sessions.")
    try:
        children = fs.list_children()
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return
    if not children:
        st.info("Create a child profile first to see learning history.")
        return
    names = {c.child_id: c.name for c in children}
    default_id = st.session_state.get("selected_child_id") or children[0].child_id
    if default_id not in names:
        default_id = children[0].child_id
    child_id = st.selectbox("Child", options=list(names.keys()), format_func=lambda cid: names[cid], index=list(names.keys()).index(default_id), key="history_child")
    st.session_state.selected_child_id = child_id
    theme.section_title("history", "Completed sessions")
    with st.container(border=True):
        _history_table(fs, child_id)