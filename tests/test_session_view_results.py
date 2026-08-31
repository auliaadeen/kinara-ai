"""Regression test for the Step 4 audit finding: Continue Learning on the
Session Success / Results screen used to pop `last_submit_result` BEFORE
attempting launch_session(). If launch_session then failed, view stayed
"results" but the key was already gone, so app.py's router
(`elif view == "results" and "last_submit_result" in st.session_state`)
silently fell through to the dashboard branch and the user lost the
results screen, even though the original session/memory update was
already safely persisted.

Fix (src/ui/session_view.py): only pop last_submit_result once
launch_session() actually returns True.

Streamlit widgets (st.button, st.rerun) are mocked directly -- this
mirrors how tests/test_session_launch.py already exercises
src/ui/session_launch.py without a full Streamlit runtime. No real
Firestore, Gemini, or OpenAI call anywhere in this file.
"""
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st

from src.ui import session_view


def _fake_session():
    return SimpleNamespace(
        title="Fractions worksheet",
        objective="Practice fractions",
        difficulty="easy",
        started_at=None,
        questions=[SimpleNamespace(id="q1", prompt="1/2 of 4?", options=["1", "2"])],
        answers={"q1": 1},
        answer_key={"q1": 1},
    )


def _fake_result():
    return SimpleNamespace(
        score=80.0,
        xp_awarded=10,
        xp_breakdown={"completion": 10},
        memory=SimpleNamespace(learning_trend="improving"),
        next_experience=SimpleNamespace(
            topic="Fractions", difficulty="easy", reason="Because recent scores improved."
        ),
    )


def _seed_session_state():
    st.session_state.clear()
    st.session_state["uid"] = "user-a"
    st.session_state["selected_child_id"] = "child-1"
    st.session_state["view"] = "results"
    st.session_state["current_session"] = _fake_session()
    st.session_state["last_submit_result"] = _fake_result()


def _click_only(label_to_click: str):
    """A st.button stand-in that reports True only for one specific
    label, False for every other button on the screen (mirrors a real
    single click)."""

    def _button(label, *args, **kwargs):
        return label == label_to_click

    return _button


# --- 1. success ---------------------------------------------------------------


def test_continue_learning_success_removes_result_and_reruns():
    _seed_session_state()

    with patch.object(st, "button", _click_only("Continue Learning")), \
         patch.object(st, "rerun") as mock_rerun, \
         patch.object(session_view, "launch_session", return_value=True) as mock_launch:
        session_view.render_results(settings=object(), db=object())

    mock_launch.assert_called_once()
    assert "last_submit_result" not in st.session_state
    mock_rerun.assert_called_once()


# --- 2. failure -----------------------------------------------------------------


def test_continue_learning_failure_keeps_result_and_results_screen_reachable():
    _seed_session_state()
    original_result = st.session_state["last_submit_result"]

    with patch.object(st, "button", _click_only("Continue Learning")), \
         patch.object(st, "rerun") as mock_rerun, \
         patch.object(session_view, "launch_session", return_value=False) as mock_launch:
        session_view.render_results(settings=object(), db=object())

    mock_launch.assert_called_once()
    # still present, and still the SAME object -- not silently replaced
    assert st.session_state.get("last_submit_result") is original_result
    # view was never touched by this handler, so the router's
    # `view == "results" and "last_submit_result" in st.session_state`
    # check still holds on the next rerun -> results screen stays reachable.
    assert st.session_state.get("view") == "results"
    mock_rerun.assert_not_called()


# --- 3. no duplicate state on failure --------------------------------------------


def test_continue_learning_failure_does_not_alter_other_session_state():
    _seed_session_state()
    original_session = st.session_state["current_session"]
    keys_before = set(st.session_state.keys())

    with patch.object(st, "button", _click_only("Continue Learning")), \
         patch.object(st, "rerun"), \
         patch.object(session_view, "launch_session", return_value=False):
        session_view.render_results(settings=object(), db=object())

    # no new session was launched into current_session, no stray keys added
    assert st.session_state.get("current_session") is original_session
    assert set(st.session_state.keys()) == keys_before


# --- 4. dashboard Continue Learning unchanged ------------------------------------


def test_dashboard_continue_learning_still_only_pops_on_success():
    """Regression guard: dashboard_view.py's Continue Learning never
    popped last_submit_result preemptively (it doesn't touch that key at
    all) -- this fix must not have changed that file or its behavior."""
    from datetime import datetime, timezone

    from tests.fakes.fake_firestore import FakeFirestoreClient

    from src.models.learning_memory import LearningMemory
    from src.services.firestore_service import FirestoreService
    from src.ui import dashboard_view

    db = FakeFirestoreClient()
    fs = FirestoreService(db, "user-a")
    child = fs.create_child("Test Child", "Grade 2", None)
    fs.save_learning_memory(
        child.child_id,
        LearningMemory(
            recent_topics=["Fractions"],
            recommended_difficulty="easy",
            last_session_at=datetime.now(timezone.utc),
        ),
    )

    st.session_state.clear()
    st.session_state["uid"] = "user-a"
    st.session_state["email"] = "a@example.com"
    st.session_state["selected_child_id"] = child.child_id

    with patch.object(st, "button", _click_only("Continue Learning")), \
         patch.object(st, "rerun") as mock_rerun, \
         patch.object(dashboard_view, "launch_session", return_value=True) as mock_launch:
        dashboard_view.render_dashboard(settings=object(), db=db)

    mock_launch.assert_called_once()
    mock_rerun.assert_called_once()
    # dashboard never stored a last_submit_result to begin with
    assert "last_submit_result" not in st.session_state


# --- 5. Practice Again unchanged --------------------------------------------------


def test_practice_again_still_clears_both_keys_and_reruns():
    _seed_session_state()

    with patch.object(st, "button", _click_only("Practice Again")), \
         patch.object(st, "rerun") as mock_rerun:
        session_view.render_results(settings=object(), db=object())

    assert st.session_state.get("view") == "dashboard"
    assert "current_session" not in st.session_state
    assert "last_submit_result" not in st.session_state
    mock_rerun.assert_called_once()
