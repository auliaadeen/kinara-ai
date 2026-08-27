"""Active learning session + results screen (UI_SPEC.md "Session")."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.services import session_service
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError


def render_session(settings, db) -> None:
    session = st.session_state.current_session

    st.title(session.title)
    st.write(session.objective)
    st.caption(f"Difficulty: {session.difficulty}")

    with st.form("answer_form"):
        answers: dict[str, int] = {}
        for i, q in enumerate(session.questions, start=1):
            choice = st.radio(
                f"{i}. {q.prompt}",
                options=list(range(len(q.options))),
                format_func=lambda idx, opts=q.options: opts[idx],
                key=f"answer_{q.id}",
            )
            answers[q.id] = choice
        submitted = st.form_submit_button("Submit")

    if submitted:
        time_spent = int((datetime.now(timezone.utc) - session.started_at).total_seconds())
        fs = FirestoreService(db, st.session_state.uid)
        try:
            result = session_service.submit_learning_session(
                fs, st.session_state.selected_child_id, session, answers, time_spent
            )
        except FirestoreUnavailableError as exc:
            st.error(str(exc))
            return
        st.session_state.last_submit_result = result
        st.session_state.view = "results"
        st.rerun()


def render_results(settings, db) -> None:
    session = st.session_state.current_session
    result = st.session_state.last_submit_result

    st.title("Results")
    st.metric("Score", f"{result.score:.0f}%")

    st.subheader("Correct / Incorrect")
    for i, q in enumerate(session.questions, start=1):
        chosen = session.answers.get(q.id)
        correct_idx = session.answer_key.get(q.id)
        is_correct = chosen == correct_idx
        icon = "✅" if is_correct else "❌"
        st.write(f"{icon} {i}. {q.prompt}")
        if not is_correct and correct_idx is not None:
            st.caption(f"Your answer: {q.options[chosen] if chosen is not None else '—'} · Correct: {q.options[correct_idx]}")

    if result.xp_breakdown:
        st.write(f"**XP earned:** +{result.xp_awarded} ({', '.join(f'{k}: +{v}' for k, v in result.xp_breakdown.items())})")
    st.write(f"**Learning trend:** {result.memory.learning_trend}")

    st.markdown("## 🧠 Kinara learned")
    st.write(result.next_experience.reason)

    if st.button("Practice Again"):
        st.session_state.view = "dashboard"
        st.session_state.pop("current_session", None)
        st.session_state.pop("last_submit_result", None)
        st.rerun()
