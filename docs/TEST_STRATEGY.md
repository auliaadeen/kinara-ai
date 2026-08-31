# Kinara AI — Test Strategy

Version: 1.0
Status: Defines minimum test expectations for this MVP submission. No CI
pipeline required (AI_RULES Rule 12) — tests are run locally via
`python -m pytest -q` before any submission/demo.

## Categories

### 1. Unit — pure logic

Everything in `src/services/gamification.py`, `src/services/adaptive_engine.py`,
`src/utils/concepts.py`. No I/O, no mocks needed — these are plain
functions in, values out. This is the highest-value test category: it's
where score, XP, mastery, streak, and adaptive-threshold bugs live.

**Minimum expectation:** every deterministic rule in FSD.md (scoring,
XP amounts, streak trigger, mastery bands, difficulty thresholds, Grade
bands, Level thresholds once implemented) has at least one test proving
the boundary behavior (just-below / at / just-above each threshold).

### 2. Integration — service + fake Firestore

`src/services/firestore_service.py`, `src/services/session_service.py`
tested against `tests/fakes/fake_firestore.py` (a minimal in-memory
stand-in — no real network, no real project). Covers the full
generate→submit→persist wiring without needing live credentials.

**Minimum expectation:** the full submit path (score → memory update →
persistence → next recommendation) is covered end-to-end at least once
against the fake, per major behavior change (this is how the
weak-concept-stuck-forever regression was caught and fixed).

### 3. Authorization / security

`tests/test_firestore_authorization.py`. Proves `FirestoreService` cannot
be made to read/write another uid's data — structural test, not just a
policy statement. Every new `FirestoreService` method must ship with a
scoping test in this file.

### 4. AI contract

`tests/test_ai_engine.py`, `tests/test_gemini_connection.py`. Two
different things, not to be confused:

- **Contract tests** (`test_ai_engine.py`) mock the Gemini client
  entirely — assert retry-once-then-fail behavior (AI-001), and that a
  valid response validates through Pydantic. No network, always run.
- **Live connectivity check** (`test_gemini_connection.py`,
  `test_firestore_connection.py`) hit the real configured project with
  real credentials. Skipped automatically when `.env` isn't present
  (e.g. CI without secrets); otherwise they run and must pass before a
  demo. Run standalone too: `python tests/test_gemini_connection.py`.

### 5. Regression

Any bug fixed in this codebase gets a test that reproduces it first,
named to describe the bug (see `test_learning_memory_progression.py` for
the pattern). This is how "concept stuck as weak forever" and "Firestore
composite index on empty collection" stay fixed.

### 6. Manual acceptance

Everything in ACCEPTANCE_TESTS.md that touches the UI directly
(login/register screens, dashboard rendering, session flow, Continue
Learning navigation, Exam History list, Grade/Level/Strike display) is
verified manually by running `streamlit run src/app.py` and walking the
flow — Streamlit UI is not unit tested in this MVP (standard practice;
see `developing-with-streamlit` guidance). DEMO-001 is the master manual
walkthrough and must pass before any submission.

## Minimum test expectations for this MVP

| Area | Automated | Manual |
|---|---|---|
| Auth (register/login/logout) | required (AUTH-001) — currently missing, see below | required |
| UID isolation | required (AUTH-002) — done | — |
| Gemini generation + retry | required (AI-001) — done | required (live check) |
| Firestore persistence | required (DATA-001) — done | — |
| Learning Memory update | required (MEM-001) — done | required |
| Adaptive recommendation | required (ADAPT-001) — done | required |
| Scoring | required (SCORE-001) — done | — |
| Exam History | — | required once implemented (HIST-001) |
| Grade | required once implemented (GRADE-001) | required |
| Level | required once implemented (LEVEL-001) | required |
| Streak / Strike Status | required (STREAK-001) — streak done, strike badge planned | required |
| Session Success / Results UI | — | required (UI-001) |
| Continue Learning | — | required once fixed (UI-002) |
| Secret handling | — | required, one-time review (SEC-001) |
| Cloud Run deploy | — | required at deploy time (DEPLOY-001) |
| End-to-end demo | — | required (DEMO-001), the one that must never fail |

"done" = already covered by the current 57-test suite. "required" with no
qualifier = expected before this MVP is considered submission-ready.

## Known gap

`src/services/auth_service.py` (register/login REST calls, ID token
verification) has no automated tests yet — flagged in AI_RULES and
ACCEPTANCE_TESTS AUTH-001. This is the one automated-test gap this
documentation round explicitly calls out for implementation.
