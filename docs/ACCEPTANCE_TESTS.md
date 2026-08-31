# Kinara AI — Acceptance Tests

Version: 3.1
Status: describes what must be true. "Status" on each item states what is
true *today* — items marked "Planned" are NOT implemented yet; do not
read them as already passing.

Superseded from v3.0: the old finer-grained IDs (SESSION-001/002,
MEMORY-001..005, ADAPT-001..004, AI-001..003, SECURITY-001) are
consolidated into the IDs below. No substantive requirement was dropped —
see each entry's "Covers" line for where the old detail lives now.

## AUTH-001 — Authentication

Given a new user, when they register with email/password, then Firebase
Authentication creates the account and the app receives a verified uid.
Given an existing user, when they log in, then they reach the dashboard
under that same uid. Given a logged-in user, when they log out, then the
session is cleared and they're returned to the login screen.

Status: **Implemented, manually verified.** No automated test for
`auth_service.py`'s register/login REST flow yet — see TEST_STRATEGY.md
"Known gap". Adding that coverage is in scope for this MVP but not done
in this documentation-only round (tests are frozen this round — see
AI_RULES.md).

## AUTH-002 — UID isolation

User A cannot read or write User B's `users/{uid}/...` documents under
any code path. uid is always the verified Firebase ID token's uid, never
client input.

Status: **Implemented and tested.** `tests/test_firestore_authorization.py`
(4 tests) proves this structurally. Covers old SECURITY-001.

## AI-001 — Gemini generation

Given a valid prompt built from child profile + Learning Memory + topic,
when Gemini is called, then a `WorksheetResponse` (title, objective,
difficulty, questions) is returned and validated with Pydantic. Given
Gemini returns invalid JSON, then the app retries once. Given it fails
twice, then a controlled error is shown and Learning Memory is not
touched.

Status: **Implemented and tested.** `tests/test_ai_engine.py` (mocked,
4 tests) covers valid/retry/fail-twice/API-error. `tests/test_gemini_connection.py`
is the live connectivity check (skipped without `.env`). Covers old
AI-001/002/003. Gemini generates content only — never the recommendation
itself (AI_SPEC.md §0).

## DATA-001 — Firestore persistence

Given a completed action (registration, child creation, session submit),
when it succeeds, then the corresponding document exists in Firestore
under `users/{uid}/...` exactly matching FIRESTORE_SCHEMA.md. Given
Firestore is unavailable, then a clear error is shown and the app never
claims success it didn't achieve (AI_RULES Rule 6).

Status: **Implemented and tested.** `tests/test_firestore_sessions.py`,
`tests/test_firestore_authorization.py`, live check in
`tests/test_firestore_connection.py`. Covers old AUTH-002 (persistence
half) and the Firestore-unavailable branch of old error-handling
requirements.

## MEM-001 — Learning Memory

Given a completed session, when it's submitted, then
`learningMemory/current` is updated: `conceptHistory` gets this session's
per-concept outcomes appended (trimmed to a 5-entry window), `masteryMap`
is recomputed from it, and `weakConcepts`/`strongConcepts` reflect the
new `masteryMap`. Given no previous history, generating the first
activity uses a documented baseline (easy difficulty, no focus concepts).
Given the user logs out and back in, Learning Memory persists unchanged.

Status: **Implemented and tested.**
`tests/test_gamification.py` (concept history/mastery functions),
`tests/test_learning_memory_progression.py` (full submit-path
integration, including the "weak concept stuck forever" regression this
fixed). Covers old MEMORY-001..005.

## ADAPT-001 — Deterministic recommendation

Given a session score, the Adaptive Engine (Python only, never Gemini —
AI_SPEC.md §0) sets:
score < 60 → difficulty easier, focus = weak concepts;
60 ≤ score < 80 → difficulty same, focus = weak concepts + reinforcement;
score ≥ 80 → difficulty harder, focus = progression.
Given a concept was already weak and is missed again, it's prioritized
over other weak concepts. The "Recommended Next" shown to the user is
built from this output, not from Gemini.

Status: **Implemented and tested.** `tests/test_adaptive_engine.py`
(12 tests, boundary-tested at 60/80), `tests/test_learning_memory_progression.py::test_recommendation_changes_when_weakness_changes`.
Covers old ADAPT-001..004.

## SCORE-001 — Scoring

`scorePercentage = correctAnswers / totalQuestions * 100`, calculated by
Python, never by Gemini (FSD.md §5).

Status: **Implemented and tested.** `tests/test_gamification.py`.

## GRADE-001 — Performance Grade

Given a session score, a deterministic Grade is computed and shown on
Session Success / Results and in Exam History: A (≥80), B (60–79),
C (40–59), D (<40) (FSD.md §5.1). Never assigned by Gemini.

Status: **Planned — implementation required.** No code exists yet. Bands
above are the specification to implement against.

## LEVEL-001 — Kinara Level / XP progression

Given a child's cumulative `totalXP`, a Kinara Level is derived: Level 1
Starter (0), Level 2 Learner (50), Level 3 Achiever (150), Level 4
Scholar (300), Level 5 Master (500) — FSD.md §11.2. Distinct from
`educationalLevel`. Displayed on the dashboard and Session Success /
Results. Not a stored field — always derived from `totalXP`.

Status: **Planned — implementation required.** No code exists yet.

## STREAK-001 — Streak / Strike Status

Given session completions, `learningMemory.streak` updates per the
calendar-day rule already implemented (FSD.md §11.1: same day = no
change, next consecutive day = +1, any gap = reset to 1). Given the
current streak and whether today's session is already completed, a
Strike Status badge is shown per FSD.md §11.3 (🔥 done today / ⏳ not yet
today / start your streak).

Status: **streak calculation implemented and tested**
(`tests/test_gamification.py`, 4 tests). **Strike Status badge display —
planned, implementation required** (no UI code shows it yet; dashboard
currently only shows the raw streak number via `st.metric`).

## UI-001 — Session Success / Results

After submitting a session, the screen shows: score, Grade, correct/
incorrect breakdown, XP earned, learning trend, "what Kinara learned"
(adaptive reasoning), updated mastery/progression, and a next
recommended action (UI_SPEC.md).

Status: **Partially implemented.** Score, correct/incorrect, XP, trend,
"Kinara learned" reasoning, and "Practice Again" are done
(`src/ui/session_view.py::render_results`). Grade display and a working
"Continue Learning" action are **planned — implementation required**
(depends on GRADE-001 and UI-002 respectively).

## UI-002 — Continue Learning

Clicking "Continue Learning" (dashboard or Session Success / Results)
takes the user directly into a new session using the current
"Recommended Next" topic/difficulty — not a no-op, not just a scroll
(FSD.md §3.4).

Status: **Planned — implementation required.** Currently a no-op button
in `src/ui/dashboard_view.py` (`if st.button("Continue Learning"): pass`).
This is the UX defect flagged in the prior code review.

## SEC-001 — Secret handling

`.env`, Firebase service account files, and API keys are never committed.
Secrets are provided via environment variables locally and via Secret
Manager / `--set-secrets` on Cloud Run — never baked into the Docker
image. uid is only ever taken from a verified Firebase ID token.

Status: **Implemented.** `.env` gitignored (verified — see SECURITY.md).
No service-account JSON anywhere in the repo. Cloud Run Secret Manager
wiring itself happens at deploy time (not yet deployed — see DEPLOY-001).

## DEPLOY-001 — Cloud Run

The application builds via the repo's `Dockerfile`, listens on
`0.0.0.0:$PORT`, and runs successfully on Cloud Run with
`--session-affinity` and `--min-instances=1` (DEPLOYMENT.md — Streamlit's
`session_state` is per-instance, so these flags prevent a user losing
their session mid-flow on autoscale).

Status: **Not yet deployed** (explicitly deferred by product decision
across this whole engagement). Dockerfile and local `streamlit run
src/app.py` both verified working.

## DEMO-001 — CRITICAL — end-to-end judge demonstration

The following sequence must work without any step producing a hidden
error or losing data:

1. Register / log in.
2. Create a child.
3. Generate a learning activity (Gemini call succeeds, content matches
   Learning Memory context).
4. Complete it — receive score and Grade.
5. Learning Memory updates (mastery/weak/strong concepts, XP, Level,
   streak / Strike Status).
6. Use "Continue Learning" to go straight into the next activity.
7. Observe the next activity reflects previous performance (topic/
   difficulty/reason cite real prior evidence).
8. Open Exam History and see this session listed with the same score/
   Grade/XP just earned.

Status: **Steps 1–3, 4 (score only), 5 (memory/XP/streak only), 7 are
implemented and pass today.** Steps 4 (Grade), 5 (Level/Strike badge), 6
(Continue Learning), and 8 (Exam History) depend on GRADE-001, LEVEL-001,
STREAK-001, UI-002, and HIST-001 respectively — **not yet implemented.**
This is the MVP-complete bar (AI_RULES Rule 10 P0) — DEMO-001 does not
pass in full until those land.

## HIST-001 — Exam History

A browsable, most-recent-first list of a child's completed sessions,
each showing date/time, topic, score, Grade, trend (as of that session
or current — implementation must pick one and document it, FSD.md §13),
status, and XP earned. Backed entirely by the existing `sessions`
subcollection — no new Firestore data required.

Status: **Planned — implementation required.** No UI or query exists for
this yet; `list_recent_sessions` already fetches the underlying data for
adaptive context but isn't exposed as a user-facing history view.
