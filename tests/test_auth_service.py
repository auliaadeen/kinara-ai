"""AUTH-001 — auth_service.py registration/login/token-verification.

Every external call (Identity Toolkit REST, firebase-admin) is mocked.
No real network, no real Firebase project touched, no credentials used.

Scope note: role handling happens in auth_view.py/firestore_service.py
(ensure_user), and logout is just clearing st.session_state in
dashboard_view.py — neither lives in auth_service.py, so neither is
tested here; this file covers exactly what auth_service.py itself does.
"""
from unittest.mock import MagicMock

import pytest

from src.config import Settings
from src.services import auth_service


def _settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        google_cloud_project="proj",
        firebase_project_id="proj",
        firebase_web_api_key="web-key",
        port=8080,
    )


def _fake_response(status_code: int, payload: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


# --- registration ------------------------------------------------------------


def test_register_success(monkeypatch):
    payload = {"localId": "uid-1", "email": "a@example.com", "idToken": "tok-1"}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(200, payload)
    )

    result = auth_service.register(_settings(), "a@example.com", "password123")

    assert result.uid == "uid-1"
    assert result.email == "a@example.com"
    assert result.id_token == "tok-1"


def test_register_email_already_exists(monkeypatch):
    payload = {"error": {"message": "EMAIL_EXISTS"}}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(400, payload)
    )

    with pytest.raises(auth_service.AuthError, match="already exists"):
        auth_service.register(_settings(), "a@example.com", "password123")


def test_register_weak_password_maps_to_friendly_message(monkeypatch):
    payload = {"error": {"message": "WEAK_PASSWORD : Password should be at least 6 characters"}}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(400, payload)
    )

    with pytest.raises(auth_service.AuthError, match="at least 6 characters"):
        auth_service.register(_settings(), "a@example.com", "abc")


# --- login ---------------------------------------------------------------------


def test_login_success(monkeypatch):
    payload = {"localId": "uid-2", "email": "b@example.com", "idToken": "tok-2"}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(200, payload)
    )

    result = auth_service.login(_settings(), "b@example.com", "password123")

    assert result.uid == "uid-2"
    assert result.id_token == "tok-2"


def test_login_invalid_credentials(monkeypatch):
    payload = {"error": {"message": "INVALID_LOGIN_CREDENTIALS"}}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(400, payload)
    )

    with pytest.raises(auth_service.AuthError, match="Incorrect email or password"):
        auth_service.login(_settings(), "b@example.com", "wrong-password")


def test_login_missing_password_falls_back_to_generic_message(monkeypatch):
    # "missing required input" case: Identity Toolkit itself rejects an
    # empty password; auth_service doesn't pre-validate, so this covers
    # what actually happens — an unmapped error code degrades gracefully
    # rather than crashing or leaking a raw API error code to the user.
    payload = {"error": {"message": "MISSING_PASSWORD"}}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(400, payload)
    )

    with pytest.raises(auth_service.AuthError, match="Authentication failed"):
        auth_service.login(_settings(), "b@example.com", "")


def test_login_unmapped_error_code_uses_generic_message(monkeypatch):
    payload = {"error": {"message": "SOME_UNMAPPED_CODE"}}
    monkeypatch.setattr(
        auth_service.requests, "post", lambda *a, **k: _fake_response(400, payload)
    )

    with pytest.raises(auth_service.AuthError, match="Authentication failed. Please try again."):
        auth_service.login(_settings(), "b@example.com", "password123")


def test_login_network_failure_raises_auth_error(monkeypatch):
    def raise_network_error(*a, **k):
        raise auth_service.requests.RequestException("connection refused")

    monkeypatch.setattr(auth_service.requests, "post", raise_network_error)

    with pytest.raises(auth_service.AuthError, match="Could not reach Firebase"):
        auth_service.login(_settings(), "b@example.com", "password123")


# --- token verification ---------------------------------------------------------


def test_verify_id_token_success(monkeypatch):
    monkeypatch.setattr(auth_service, "get_app", lambda settings: None)
    monkeypatch.setattr(auth_service.admin_auth, "verify_id_token", lambda token: {"uid": "uid-3"})

    uid = auth_service.verify_id_token(_settings(), "some-token")

    assert uid == "uid-3"


def test_verify_id_token_failure_raises_auth_error(monkeypatch):
    monkeypatch.setattr(auth_service, "get_app", lambda settings: None)

    def raise_verification_error(token):
        raise ValueError("invalid token")

    monkeypatch.setattr(auth_service.admin_auth, "verify_id_token", raise_verification_error)

    with pytest.raises(auth_service.AuthError, match="Session expired or invalid"):
        auth_service.verify_id_token(_settings(), "bad-token")


def test_verify_id_token_never_uses_client_supplied_uid(monkeypatch):
    """DATA_MODEL.md 'never trust client-provided UID' — the uid returned
    must come only from the decoded token, never echo back caller input."""
    monkeypatch.setattr(auth_service, "get_app", lambda settings: None)
    monkeypatch.setattr(
        auth_service.admin_auth, "verify_id_token", lambda token: {"uid": "server-verified-uid"}
    )

    uid = auth_service.verify_id_token(_settings(), "arbitrary-client-string-not-a-real-uid")

    assert uid == "server-verified-uid"
