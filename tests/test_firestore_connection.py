"""Live Firestore connectivity check.

Confirms the configured Firebase project (src.config, never hardcoded here)
is actually reachable with local Application Default Credentials — writes
and reads back one throwaway document, then deletes it. Requires real
credentials and network, so it's skipped rather than failing the rest of
the suite when .env isn't configured (e.g. CI without secrets). Never
prints or asserts on any secret.

Runnable two ways from the repository root:
    python -m pytest tests/test_firestore_connection.py
    python tests/test_firestore_connection.py
The sys.path bootstrap below (derived from this file's own location, not a
hardcoded path) is what makes the second form work without a package
install or a global PYTHONPATH change.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.config import ConfigError, load_settings
from src.services.firebase_bootstrap import get_firestore_client

HEALTHCHECK_DOC = ("_kinara_healthcheck", "local_test")


def _check_firestore_reachable() -> str:
    """Pure check, no pytest dependency, so it also works as a plain script.
    Returns the project id that was confirmed reachable; raises otherwise."""
    settings = load_settings()  # raises ConfigError if .env is incomplete
    db = get_firestore_client(settings)

    collection, doc_id = HEALTHCHECK_DOC
    doc_ref = db.collection(collection).document(doc_id)
    try:
        doc_ref.set({"status": "ok", "source": "local-development"})
        doc = doc_ref.get()
        if not doc.exists:
            raise RuntimeError("Firestore write succeeded but the document was not found on read-back")
    finally:
        doc_ref.delete()  # leave no debug clutter in the real project

    return settings.firebase_project_id


def test_firestore_is_reachable():
    import pytest

    try:
        project_id = _check_firestore_reachable()
    except ConfigError:
        pytest.skip("Firebase not configured (.env missing) — skipping live connection check")
    except Exception as exc:
        pytest.fail(f"Firestore is not reachable: {exc}")
    assert project_id


if __name__ == "__main__":
    try:
        reachable_project = _check_firestore_reachable()
    except ConfigError as exc:
        print(f"SKIPPED: {exc}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
    else:
        print(f"PASS: Firestore project '{reachable_project}' is reachable.")
