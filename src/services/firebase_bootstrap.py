"""One-time Firebase Admin SDK init (Firestore + Auth verification).

Uses Application Default Credentials only — no service account JSON is ever
read from a committed path (SECURITY.md). Locally, run
`gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS
to point at an untracked key file. On Cloud Run, ADC resolves automatically
from the attached service account.
"""
from __future__ import annotations

import firebase_admin
from firebase_admin import credentials, firestore

from src.config import Settings

_app: firebase_admin.App | None = None


def get_app(settings: Settings) -> firebase_admin.App:
    global _app
    if _app is None:
        cred = credentials.ApplicationDefault()
        _app = firebase_admin.initialize_app(
            cred, {"projectId": settings.firebase_project_id}
        )
    return _app


def get_firestore_client(settings: Settings):
    get_app(settings)
    return firestore.client()
