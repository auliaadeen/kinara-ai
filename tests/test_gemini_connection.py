"""Live Gemini connectivity check.

Confirms GEMINI_MODEL (from src.config, never hardcoded here) is actually
reachable with the configured API key. Requires real credentials and
network, so it's skipped rather than failing the rest of the suite when
.env isn't configured (e.g. CI without secrets). Never prints or asserts
on GEMINI_API_KEY itself.

Runnable two ways from the repository root:
    python -m pytest tests/test_gemini_connection.py
    python tests/test_gemini_connection.py
The sys.path bootstrap below (derived from this file's own location, not a
hardcoded path) is what makes the second form work without a package
install or a global PYTHONPATH change.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from google import genai

from src.config import ConfigError, load_settings

EXPECTED_REPLY = "KINARA GEMINI OK"


def _check_gemini_reachable() -> str:
    """Pure check, no pytest dependency, so it also works as a plain script.
    Returns the model name that was confirmed reachable; raises otherwise."""
    settings = load_settings()  # raises ConfigError if .env is incomplete
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=f"Reply with exactly: {EXPECTED_REPLY}",
    )
    if not response.text or EXPECTED_REPLY not in response.text:
        raise RuntimeError(
            f"Unexpected response from model '{settings.gemini_model}': {response.text!r}"
        )
    return settings.gemini_model


def test_gemini_model_is_reachable():
    import pytest

    try:
        model = _check_gemini_reachable()
    except ConfigError:
        pytest.skip("Gemini not configured (.env missing) — skipping live connection check")
    except Exception as exc:
        pytest.fail(f"Gemini model is not reachable: {exc}")
    assert model


if __name__ == "__main__":
    try:
        reachable_model = _check_gemini_reachable()
    except ConfigError as exc:
        print(f"SKIPPED: {exc}")
        sys.exit(0)
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
    else:
        print(f"PASS: Gemini model '{reachable_model}' is reachable.")
