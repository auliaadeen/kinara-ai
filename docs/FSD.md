# Kinara AI — Functional Specification Document

Version: 3.1
Status: LOCKED

## 1. Functional Principle

Kinara must implement this loop:

LEARN
→ TEST
→ SCORE
→ REMEMBER
→ ANALYZE
→ ADAPT
→ RECOMMENDED NEXT
→ LEARN AGAIN

(Same loop as v3.0's LEARN→ASSESS→REMEMBER→ADAPT→GENERATE→NEXT
EXPERIENCE, restated with SCORE and ANALYZE broken out explicitly because
each is its own deterministic Python step — see ARCHITECTURE.md §3/§4.)

## 2. Authentication

Firebase Authentication is the source of identity.

Supported:

- Email/password registration
- Email/password login
- logout

Each authenticated user receives:

uid
email
role

Roles:

parent
learner

Never use email as the primary database identifier.

Use Firebase UID.

## 3. Parent Workspace

### 3.1 Create Child

Required:

- name
- educational level

Optional:

- preferred learning style

System generates:

- childId
- initial XP
- initial streak
- initial learning memory

### 3.2 Child Dashboard

Display:

- child name
- educational level
- XP
- Kinara Level (planned — implementation required, §11.2)
- streak and Strike Status (planned — implementation required, §11.3)
- mastery overview
- weak concepts
- strong concepts
- recommended next activity
- link/section to Exam History (planned — implementation required, §14)

### 3.3 Generate Learning Experience

Input:

- childId
- topic
- optional difficulty

System:

1. Load child profile.
2. Load learning memory.
3. Load recent sessions.
4. Run adaptive engine. (Python only — Gemini is not called yet at this point, and never makes this decision. See §8.)
5. Build Gemini prompt.
6. Request structured JSON.
7. Validate response.
8. Display learning activity.

If learning history exists, it MUST be included in the adaptive context.

### 3.4 Continue Learning (planned — implementation required)

"Continue Learning" is a CTA shown on the dashboard's "Recommended Next"
section (UI_SPEC.md) and on the Session Success / Results screen after a
session (§9, §12). It is currently a no-op button — flagged as a UX
defect (ACCEPTANCE_TESTS.md UI-002).

**Required behavior:** clicking it must invoke the same
"Generate Learning Experience" flow (§3.3) using the currently
recommended topic and difficulty (from §9's Next Experience output) as
the input, without requiring the parent to re-enter them manually. It
must land the user directly in an active session, not merely scroll to
or highlight a form.

This does not require a new navigation system — it's a pre-filled
trigger into the flow that already exists.

## 4. Learning Session

A learning session contains:

- sessionId
- topic
- difficulty
- generated activity
- questions/tasks
- answer key
- startedAt
- completedAt
- answers
- score
- behavior signals
- memory snapshot

## 5. Assessment

For MVP, objective questions are preferred.

System calculates:

scorePercentage =
correctAnswers / totalQuestions * 100

Do not allow Gemini to determine the final score.

The application calculates the score.

### 5.1 Grade (planned — implementation required)

Grade is a deterministic performance classification computed by Python
from `scorePercentage`, distinct from `educationalLevel` (school grade,
e.g. "Grade 3" — an input, not a result). Never assigned by Gemini
(AI_SPEC.md §5).

| Grade | Label | Score range |
|---|---|---|
| A | Excellent | score ≥ 80 |
| B | Good | 60 ≤ score < 80 |
| C | Fair | 40 ≤ score < 60 |
| D | Needs Improvement | score < 40 |

The 60/80 breakpoints are the same ones already used by the Adaptive
Engine (§8) — Grade is a label over the same evidence, not a second
threshold scheme.

## 6. Behavior Signals

After completion:

- score
- incorrect questions
- attempt count
- completion
- time spent
- difficulty
- topic
- concept errors

These signals become Learning Memory evidence.

## 7. Learning Memory

Learning Memory represents accumulated evidence about the learner.

Minimum fields:

- masteryMap
- conceptHistory (recency-weighted evidence window per concept — see
  DATA_MODEL.md / FIRESTORE_SCHEMA.md for the exact structure and
  relationship to masteryMap)
- weakConcepts
- strongConcepts
- recentTopics
- difficulty
- learningTrend
- totalXP
- streak
- lastSessionAt

## 8. Adaptive Engine

The Adaptive Engine determines the next learning direction. **This is
100% deterministic Python** (`src/services/adaptive_engine.py`) —
Gemini is never asked to make this decision (AI_SPEC.md §0). Preserve
these thresholds and behavior exactly as already implemented; nothing in
this documentation round changes them.

Example rules:

score < 60:
difficulty = easier
focus = weak concepts

60 <= score < 80:
difficulty = same
focus = weak concepts + reinforcement

score >= 80:
difficulty = harder
focus = progression

Repeated errors:
prioritize repeated weak concept.

Strong improvement:
allow progression.

## 9. Next Experience

The system must produce:

- recommended topic
- recommended difficulty
- learning objective
- reason

Example:

Recommended Topic:
Comparing Fractions

Difficulty:
Medium

Reason:
"Your previous sessions show improvement in identifying fractions, but comparison remains a weak concept."

This output feeds the "Continue Learning" CTA (§3.4) — clicking it must
generate the next session using exactly this recommendation.

## 10. Self-Learner — DEFERRED

Not implemented. Do not implement or expand for this MVP/submission.
Kept as target end-state description only:

Input:

- learning goal
- target duration

System:

1. creates learning path
2. creates modules
3. tracks completion
4. records performance
5. updates memory
6. recommends next module/activity

## 11. Gamification

XP is deterministic.

Examples:

complete session = +10 XP
score >= 80 = +10 XP
improvement = +5 XP
streak = +5 XP

Gamification must reflect actual activity.

Do not randomly assign XP.

### 11.1 Streak (implemented, documented as-built)

Calendar-day based, not session-count based:

- learner completes a session on a new calendar day, consecutive to
  `lastSessionAt`'s day → streak + 1
- learner completes a second session on the *same* calendar day →
  streak unchanged
- a gap of more than one calendar day → streak resets to 1

This rule was an implementation assumption (FSD v3.0 didn't specify a
streak trigger); documented here as the actual, confirmed behavior going
forward.

### 11.2 Kinara Level (planned — implementation required)

Distinct from `educationalLevel` (school grade). Derived from cumulative
`totalXP`, computed by Python, never by Gemini. Simple fixed thresholds,
no formula:

| Level | Name | Min cumulative XP |
|---|---|---|
| 1 | Starter | 0 |
| 2 | Learner | 50 |
| 3 | Achiever | 150 |
| 4 | Scholar | 300 |
| 5 | Master | 500 |

Level is derived at read time from `totalXP` — not a stored field (see
FIRESTORE_SCHEMA.md). Displayed on the Child Dashboard (§3.2) and Session
Success / Results (§12) alongside XP.

### 11.3 Strike Status (planned — implementation required)

Distinguishes three things, all derived from existing data — no new
mechanics, no new persisted field:

- **current streak** — `learningMemory.streak` (already implemented, §11.1)
- **today completed** — `learningMemory.lastSessionAt`'s calendar date
  equals today's calendar date
- **status badge** shown to the user:
  - streak ≥ 1 and today completed → "🔥 {streak}-day streak — today done"
  - streak ≥ 1 and today not completed → "⏳ {streak}-day streak — complete today's activity to keep it"
  - streak = 0 → "Start your streak today"

## 12. Session Success / Results

(Official terminology for the post-submit screen — see UI_SPEC.md.)

Must surface:

- score
- Grade (planned — implementation required, §5.1)
- correct/incorrect breakdown
- XP earned
- learning trend
- what Kinara learned (adaptive reasoning, §9)
- updated mastery/progression where appropriate
- next recommended action ("Continue Learning", §3.4)

## 13. Exam History (planned — implementation required)

A browsable list of the child's completed sessions, backed by the
existing `sessions` subcollection (no new Firestore data — see
FIRESTORE_SCHEMA.md). Must show, at minimum, per entry:

- date/time (`completedAt`)
- topic
- score
- Grade (§5.1)
- previous/relevant trend at that point (`learningTrend` is a snapshot
  on the memory doc at write time, not per-session — showing the trend
  *as of* each session requires either reading it from the session's own
  behavior-signal data or accepting the current overall trend as an
  approximation; implementation must pick one and document which)
- status/result (completed; incomplete sessions are excluded, matching
  `list_recent_sessions`' existing `completed == True` filtering)
- XP earned for that session

Must let the parent/learner understand progression over time (e.g.
ordered most-recent-first, matching the existing `completedAt`
descending order already used elsewhere). Does not require redesigning
the rest of the dashboard — additive section/view only.

## 14. Error Handling

Gemini failure:

- show friendly error
- do not corrupt learning memory

Invalid Gemini JSON:

- retry once
- if still invalid, fail gracefully

Firestore unavailable:

- show clear system error
- do not pretend data was persisted

Authentication failure:

- show authentication error

## 15. Non-Goals

MVP does NOT include:

- multi-agent architecture
- real-time collaboration
- payment
- mobile native app
- complex recommendation ML
- vector database
- RAG
- external content scraping
- automated PDF generation
- teacher marketplace
- Self-Learner mode (§10)
- CI pipeline (TEST_STRATEGY.md)
