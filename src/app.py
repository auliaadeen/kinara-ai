"""Zunara AI — Streamlit entrypoint."""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st

from src.config import ConfigError, load_settings
from src.services.firebase_bootstrap import get_firestore_client
from src.ui import theme
from src.ui.auth_view import render_auth
from src.ui.dashboard_view import render_dashboard, render_history
from src.ui.learner_view import render_learner_dashboard, render_learner_history
from src.ui.session_view import render_results, render_session

st.set_page_config(page_title="Zunara AI", page_icon=":material/psychology:", layout="centered")

_SESSION_KEYS = ["uid", "email", "id_token", "role", "view", "selected_child_id", "current_session", "last_submit_result"]


def _logout() -> None:
    for key in _SESSION_KEYS:
        st.session_state.pop(key, None)
    st.rerun()


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as exc:
        st.error(f"Configuration error: {exc}")
        st.stop()
        return

    try:
        db = get_firestore_client(settings)
    except Exception as exc:
        st.error(
            "Could not connect to Firebase. Check FIREBASE_PROJECT_ID and that Application "
            f"Default Credentials are available. ({exc})"
        )
        st.stop()
        return

    if "uid" not in st.session_state:
        theme.inject()
        render_auth(settings, db)
        return

    theme.inject()
    role = st.session_state.get("role", "parent")
    view = st.session_state.get("view", "dashboard")
    theme.render_identity_sidebar(st.session_state.get("email"), view, _logout, role=role)

    if view == "session" and "current_session" in st.session_state:
        render_session(settings, db)
    elif view == "results" and "last_submit_result" in st.session_state:
        render_results(settings, db)
    elif view == "history":
        if role == "learner":
            render_learner_history(db)
        else:
            render_history(db)
    elif role == "learner":
        render_learner_dashboard(settings, db)
    else:
        st.session_state.view = "dashboard"
        render_dashboard(settings, db)


if __name__ == "__main__":
    main()
