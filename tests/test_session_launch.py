"""UI-002 regression test.

"Continue Learning" was an inert no-op button. This proves the shared
launch_session() helper it (and the manual Generate form) now go through
actually invokes generation with the given topic/difficulty and switches
the view — not a silent pass. Also proves it does NOT compute a second
recommendation itself (it takes topic/difficulty as plain arguments and
passes them straight through).
"""
import streamlit as st

from src.services import session_service
from src.ui.session_launch import launch_session


def test_launch_session_success_sets_view_and_session(monkeypatch):
    fake_session = object()
    monkeypatch.setattr(
        "src.ui.session_launch.session_service.generate_learning_experience",
        lambda settings, fs, child_id, topic, difficulty: fake_session,
    )
    st.session_state.clear()

    result = launch_session(settings=object(), fs=object(), child_id="c1", topic="Fractions", difficulty="easy")

    assert result is True
    assert st.session_state["current_session"] is fake_session
    assert st.session_state["view"] == "session"


def test_launch_session_passes_through_the_given_topic_and_difficulty(monkeypatch):
    calls = []

    def fake_generate(settings, fs, child_id, topic, difficulty):
        calls.append((topic, difficulty))
        return object()

    monkeypatch.setattr("src.ui.session_launch.session_service.generate_learning_experience", fake_generate)
    st.session_state.clear()

    launch_session(settings=object(), fs=object(), child_id="c1", topic="Comparing Fractions", difficulty="hard")

    assert calls == [("Comparing Fractions", "hard")]


def test_launch_session_failure_does_not_change_view(monkeypatch):
    def raise_child_not_found(settings, fs, child_id, topic, difficulty):
        raise session_service.ChildNotFoundError("nope")

    monkeypatch.setattr(
        "src.ui.session_launch.session_service.generate_learning_experience", raise_child_not_found
    )
    st.session_state.clear()
    st.session_state["view"] = "dashboard"

    result = launch_session(settings=object(), fs=object(), child_id="c1", topic="Fractions", difficulty=None)

    assert result is False
    assert st.session_state["view"] == "dashboard"
    assert "current_session" not in st.session_state
