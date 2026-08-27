"""Login / registration screen (FSD.md #2)."""
from __future__ import annotations

import streamlit as st

from src.config import Settings
from src.services import auth_service
from src.services.firestore_service import FirestoreService, FirestoreUnavailableError


def _enter_app(settings: Settings, db, uid: str, email: str, id_token: str, role: str | None) -> None:
    fs = FirestoreService(db, uid)
    try:
        user = fs.ensure_user(email=email, role=role or "parent")
    except FirestoreUnavailableError as exc:
        st.error(str(exc))
        return

    st.session_state.uid = uid
    st.session_state.email = email
    st.session_state.id_token = id_token
    st.session_state.role = user.role
    st.session_state.view = "dashboard"
    st.rerun()


def render_auth(settings: Settings, db) -> None:
    st.title("Kinara AI")
    st.caption("AI remembers learning behavior and adapts the next learning experience.")

    login_tab, register_tab = st.tabs(["Log in", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            try:
                result = auth_service.login(settings, email, password)
                uid = auth_service.verify_id_token(settings, result.id_token)
            except auth_service.AuthError as exc:
                st.error(str(exc))
            else:
                _enter_app(settings, db, uid, result.email, result.id_token, role=None)

    with register_tab:
        with st.form("register_form"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            role = st.selectbox("I am a...", options=["parent", "learner"], key="register_role")
            submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                result = auth_service.register(settings, email, password)
                uid = auth_service.verify_id_token(settings, result.id_token)
            except auth_service.AuthError as exc:
                st.error(str(exc))
            else:
                _enter_app(settings, db, uid, result.email, result.id_token, role=role)
