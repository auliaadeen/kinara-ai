"""Active learning session + results screen (UI_SPEC.md "Session").

BATCH 1 — frontend/UI/UX only. Scoring, submission, and the
Continue-Learning/Practice-Again control flow (including the Step 4
audit fix: only pop `last_submit_result` once `launch_session()` actually
returns True) are unchanged — only presentation was touched. See
src/ui/theme.py for the shared design system.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.services import gamification, session_service
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError
from src.ui import theme
from src.ui.session_launch import launch_session


def render_session(settings, db) -> None:
    session = st.session_state.current_session

    theme.hero("Learning session", session.title, session.objective)
    st.caption(f"{len(session.questions)} questions · Difficulty: {session.difficulty}")

    with st.form("answer_form"):
        answers: dict[str, int] = {}
        for i, q in enumerate(session.questions, start=1):
            with st.container(border=True):
                st.markdown(f"**Question {i} of {len(session.questions)}**")
                choice = st.radio(
                    q.prompt,
                    options=list(range(len(q.options))),
                    format_func=lambda idx, opts=q.options: opts[idx],
                    key=f"answer_{q.id}",
                )
                answers[q.id] = choice
        submitted = st.form_submit_button("Submit", icon=":material/task_alt:", type="primary", width="stretch")

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

    theme.hero("Session complete", "Nice work!", "Here's what Kinara saw, and what's next.")

    grade_letter, grade_label = gamification.compute_grade(result.score)
    col1, col2 = st.columns(2)
    col1.metric("Score", f"{result.score:.0f}%")
    col2.metric("Grade", f"{grade_letter} — {grade_label}")

    if result.xp_breakdown:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.badge(f"+{result.xp_awarded} XP", icon=":material/bolt:", color="orange")
            st.caption(", ".join(f"{k}: +{v}" for k, v in result.xp_breakdown.items()))
    st.caption(f"Learning trend: {result.memory.learning_trend}")

    theme.section_title("fact_check", "Correct / incorrect")
    with st.container(border=True):
        for i, q in enumerate(session.questions, start=1):
            chosen = session.answers.get(q.id)
            correct_idx = session.answer_key.get(q.id)
            is_correct = chosen == correct_idx
            with st.container(horizontal=True, vertical_alignment="center"):
                if is_correct:
                    st.badge("Correct", icon=":material/check_circle:", color="green")
                else:
                    st.badge("Incorrect", icon=":material/cancel:", color="red")
                st.write(f"{i}. {q.prompt}")
            if not is_correct and correct_idx is not None:
                st.caption(
                    f"Your answer: {q.options[chosen] if chosen is not None else '—'} · "
                    f"Correct: {q.options[correct_idx]}"
                )

    theme.section_title("psychology", "Kinara learned")
    with st.container(border=True):
        st.write(result.next_experience.reason)

    theme.section_title("auto_awesome", "Recommended next")
    with st.container(key=theme.CTA_KEY, border=True):
        theme.cta_eyebrow("bolt", "Kinara's pick for today")
        st.markdown(f"#### {result.next_experience.topic}")
        st.caption(f"Difficulty: {result.next_experience.difficulty}")
        if st.button("Continue Learning", type="primary", icon=":material/play_arrow:", width="stretch"):
            # Reuses result.next_experience (already computed at submit
            # time) directly — no second recommendation, no extra Gemini
            # call for the decision itself (UI-002, AI_SPEC.md §0).
            fs = FirestoreService(db, st.session_state.uid)
            rec = result.next_experience
            # Only clear last_submit_result once launch_session actually
            # succeeds — clearing it beforehand meant a failed attempt
            # left view=="results" but the key gone, so app.py's router
            # silently bounced the user to the dashboard and they lost
            # this screen (Step 4 audit finding). The original completed
            # session/memory update is unaffected either way; this is
            # purely about which screen is shown next.
            if launch_session(settings, fs, st.session_state.selected_child_id, rec.topic, rec.difficulty):
                st.session_state.pop("last_submit_result", None)
                st.rerun()

    if st.button("Practice Again", icon=":material/replay:"):
        st.session_state.view = "dashboard"
        st.session_state.pop("current_session", None)
        st.session_state.pop("last_submit_result", None)
        st.rerun()
