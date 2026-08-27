"""Parent dashboard (UI_SPEC.md, FSD.md #3)."""
from __future__ import annotations

import streamlit as st

from src.config import Settings
from src.models.common import DIFFICULTY_ORDER
from src.services import adaptive_engine, session_service
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.services.ai_engine import AIGenerationError


def _create_child_form(fs: FirestoreService) -> None:
    with st.expander("+ Add a child", expanded=False):
        with st.form("create_child_form"):
            name = st.text_input("Name")
            level = st.text_input("Educational level (e.g. Grade 2)")
            style = st.text_input("Preferred learning style (optional)")
            submitted = st.form_submit_button("Create child")
        if submitted:
            if not name.strip() or not level.strip():
                st.error("Name and educational level are required.")
                return
            try:
                fs.create_child(name.strip(), level.strip(), style.strip() or None)
            except FirestoreUnavailableError as exc:
                st.error(str(exc))
            else:
                st.success(f"{name} added.")
                st.rerun()


def _generate_form(settings: Settings, fs: FirestoreService, child_id: str, default_topic: str, default_difficulty: str) -> None:
    st.subheader("Generate Learning Experience")
    with st.form("generate_form"):
        topic = st.text_input("Topic", value=default_topic)
        difficulty = st.selectbox(
            "Difficulty (optional override)",
            options=["(use recommended)"] + list(DIFFICULTY_ORDER),
            index=(["(use recommended)"] + list(DIFFICULTY_ORDER)).index(default_difficulty)
            if default_difficulty in DIFFICULTY_ORDER
            else 0,
        )
        submitted = st.form_submit_button("Generate")
    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
            return
        override = None if difficulty == "(use recommended)" else difficulty
        with st.spinner("Kinara is preparing the activity..."):
            try:
                session = session_service.generate_learning_experience(
                    settings, fs, child_id, topic.strip(), override
                )
            except session_service.ChildNotFoundError as exc:
                st.error(str(exc))
                return
            except FirestoreUnavailableError as exc:
                st.error(str(exc))
                return
            except AIGenerationError as exc:
                st.error(str(exc))
                return
        st.session_state.current_session = session
        st.session_state.view = "session"
        st.rerun()


def render_dashboard(settings: Settings, db) -> None:
    fs = FirestoreService(db, st.session_state.uid)

    with st.sidebar:
        st.write(f"Signed in as **{st.session_state.email}**")
        if st.button("Log out"):
            for key in ["uid", "email", "id_token", "role", "view", "selected_child_id", "current_session", "last_submit_result"]:
                st.session_state.pop(key, None)
            st.rerun()

    st.title("Kinara AI")

    try:
        children = fs.list_children()
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    _create_child_form(fs)

    if not children:
        st.info("Create a child profile to get started.")
        return

    names = {c.child_id: c.name for c in children}
    default_id = st.session_state.get("selected_child_id") or children[0].child_id
    if default_id not in names:
        default_id = children[0].child_id
    child_id = st.selectbox(
        "Child", options=list(names.keys()), format_func=lambda cid: names[cid],
        index=list(names.keys()).index(default_id),
    )
    st.session_state.selected_child_id = child_id

    try:
        child = fs.get_child(child_id)
        memory = fs.get_learning_memory(child_id)
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    st.caption(f"{child.educational_level}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("XP", memory.total_xp)
    col2.metric("Streak", memory.streak)
    avg_mastery = round(sum(memory.mastery_map.values()) / len(memory.mastery_map), 1) if memory.mastery_map else 0
    col3.metric("Mastery", f"{avg_mastery}%")
    col4.metric("Trend", memory.learning_trend)

    st.markdown("## 🧠 What Kinara Remembers")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.write("**Weak concepts**")
        st.write(", ".join(c.replace("_", " ") for c in memory.weak_concepts) or "None yet")
    with r2:
        st.write("**Strong concepts**")
        st.write(", ".join(c.replace("_", " ") for c in memory.strong_concepts) or "None yet")
    with r3:
        st.write("**Recent topics**")
        st.write(", ".join(memory.recent_topics) or "None yet")

    st.markdown("## 🎯 Recommended Next")
    default_topic = ""
    default_difficulty = memory.recommended_difficulty
    if memory.has_history and memory.recent_topics:
        rec = adaptive_engine.build_next_experience(
            updated_memory=memory, last_topic=memory.recent_topics[0], repeated_weak_concept=None
        )
        st.write(f"**Topic:** {rec.topic}")
        st.write(f"**Difficulty:** {rec.difficulty}")
        st.write(f"**Reason:** {rec.reason}")
        default_topic = rec.topic
        if st.button("Continue Learning"):
            pass  # form below is already pre-filled; explicit button just anchors intent
    else:
        st.write("No learning history yet — generate the first activity below.")

    _generate_form(settings, fs, child_id, default_topic, default_difficulty)
