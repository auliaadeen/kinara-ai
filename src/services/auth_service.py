"""Firebase Authentication (SECURITY.md, FSD.md #2).

Streamlit has no Firebase client SDK, so password sign-up/sign-in goes
through the Identity Toolkit REST API (needs the public Web API key), and
every ID token that comes back is verified server-side with firebase-admin
before its uid is trusted for anything. The uid used everywhere downstream
always comes from a verified token, never from client input
(DATA_MODEL.md "Never trust client-provided UID").
"""
from __future__ import annotations

import requests
from firebase_admin import auth as admin_auth

from src.config import Settings
from src.services.firebase_bootstrap import get_app

_IDENTITY_TOOLKIT_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


class AuthError(RuntimeError):
    """Raised on registration/login/logout failure (FSD.md #12)."""


class AuthResult:
    def __init__(self, uid: str, email: str, id_token: str):
        self.uid = uid
        self.email = email
        self.id_token = id_token


def _post(endpoint: str, settings: Settings, payload: dict) -> dict:
    url = f"{_IDENTITY_TOOLKIT_BASE}:{endpoint}"
    try:
        resp = requests.post(
            url, params={"key": settings.firebase_web_api_key}, json=payload, timeout=15
        )
    except requests.RequestException as exc:
        raise AuthError("Could not reach Firebase Authentication. Try again.") from exc

    data = resp.json()
    if resp.status_code != 200:
        message = data.get("error", {}).get("message", "AUTH_ERROR")
        raise AuthError(_friendly_message(message))
    return data


def _friendly_message(code: str) -> str:
    known = {
        "EMAIL_EXISTS": "An account with this email already exists.",
        "EMAIL_NOT_FOUND": "No account found with this email.",
        "INVALID_PASSWORD": "Incorrect password.",
        "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
        "WEAK_PASSWORD : Password should be at least 6 characters": "Password must be at least 6 characters.",
    }
    return known.get(code, "Authentication failed. Please try again.")


def register(settings: Settings, email: str, password: str) -> AuthResult:
    data = _post(
        "signUp", settings, {"email": email, "password": password, "returnSecureToken": True}
    )
    return AuthResult(uid=data["localId"], email=data["email"], id_token=data["idToken"])


def login(settings: Settings, email: str, password: str) -> AuthResult:
    data = _post(
        "signInWithPassword",
        settings,
        {"email": email, "password": password, "returnSecureToken": True},
    )
    return AuthResult(uid=data["localId"], email=data["email"], id_token=data["idToken"])


def verify_id_token(settings: Settings, id_token: str) -> str:
    """Return the verified uid, or raise AuthError. This is the only trusted
    source of uid in the whole application."""
    get_app(settings)
    try:
        decoded = admin_auth.verify_id_token(id_token)
    except Exception as exc:  # firebase_admin raises several distinct exception types
        raise AuthError("Session expired or invalid. Please log in again.") from exc
    return decoded["uid"]
