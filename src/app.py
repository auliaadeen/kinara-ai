"""Kinara AI — Streamlit entrypoint (ARCHITECTURE.md #1, #2).

`streamlit run src/app.py` executes this file directly, the same way plain
`python src/app.py` would: sys.path[0] is set to this file's own directory
(src/), never the repository root. That leaves the `src` package itself
unreachable for the `from src.xxx import ...` imports below (and for every
module they in turn import), since `src` needs to be found as a package one
level up, not from inside itself. This bootstrap puts the repo root on
sys.path before anything under `src` is imported — no global PYTHONPATH
change, no hardcoded path (derived from this file's own location).
"""
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
from src.ui.dashboard_view import render_dashboard
from src.ui.session_view import render_results, render_session

st.set_page_config(page_title="Kinara AI", page_icon=":material/psychology:", layout="centered")

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
    except Exception as exc:  # ADC / Firebase project misconfiguration
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
    view = st.session_state.get("view", "dashboard")
    theme.render_identity_sidebar(st.session_state.get("email"), view, _logout)

    if view == "session" and "current_session" in st.session_state:
        render_session(settings, db)
    elif view == "results" and "last_submit_result" in st.session_state:
        render_results(settings, db)
    else:
        st.session_state.view = "dashboard"
        render_dashboard(settings, db)


if __name__ == "__main__":
    main()
