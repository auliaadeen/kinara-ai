# Kinara AI — Firestore Schema

Version: 3.1
Status: Canonical schema reference. Reflects `src/models/` and
`src/services/firestore_service.py` as implemented. This document, not
DATA_MODEL.md's prose sketch, is authoritative on exact field names/types;
DATA_MODEL.md stays as the human-readable overview and must not contradict
this file.

## Design rule (unchanged)

Every document lives under `users/{uid}/...`. `FirestoreService` is
constructed with one verified `uid` and has no method that accepts a
caller-supplied uid for another user's data — cross-user access is
structurally impossible, not just policy-enforced (SECURITY.md,
FIRESTORE_SCHEMA SEC-001).

Firestore Security Rules (`firestore.rules`) are deny-all. The Admin SDK
(server-side only, via Application Default Credentials) bypasses rules
entirely — no client ever talks to Firestore directly in this
architecture, so the deny-all rule set is defense-in-depth, not the actual
enforcement boundary. The actual boundary is: uid only ever comes from a
verified Firebase ID token (`auth_service.verify_id_token`), never from
client-supplied input.

## Collections

### `users/{uid}`

```
{
  uid: string,
  email: string,
  role: "parent" | "learner",
  createdAt: timestamp
}
```

Created on first login/registration (`FirestoreService.ensure_user`). uid
is the Firebase Auth UID — email is never used as a document ID or lookup
key anywhere in the codebase.

### `users/{uid}/children/{childId}`

```
{
  childId: string,       // uuid4, generated server-side
  name: string,
  educationalLevel: string,   // e.g. "Grade 3" — school grade, NOT the
                               // performance Grade defined below
  preferredLearningStyle: string | null,
  xp: number,             // mirrors learningMemory/current.totalXP
  streak: number,          // mirrors learningMemory/current.streak
  createdAt: timestamp,
  updatedAt: timestamp
}
```

`xp`/`streak` are kept in sync with the memory doc on every session submit
(`FirestoreService.update_child_xp_streak`) so the dashboard can read
either without an extra query.

### `users/{uid}/children/{childId}/learningMemory/current`

Singleton document (fixed id `current`), created empty at child creation,
overwritten wholesale after every completed session.

```
{
  masteryMap: { [conceptSlug: string]: number },   // 0..100, recency-weighted
  conceptHistory: { [conceptSlug: string]: boolean[] },  // see DATA_MODEL.md
  weakConcepts: string[],     // conceptSlug where masteryMap value < 50
  strongConcepts: string[],   // conceptSlug where masteryMap value >= 80
  recentTopics: string[],     // last 5 distinct topics, most recent first
  recommendedDifficulty: "easy" | "medium" | "hard",
  learningTrend: "improving" | "declining" | "stable",
  totalXP: number,
  streak: number,
  lastSessionAt: timestamp | null,
  updatedAt: timestamp
}
```

Concept slugs are normalized (`src/utils/concepts.py::normalize_concept`)
before ever reaching this document — lowercase, underscore-separated.

### `users/{uid}/children/{childId}/sessions/{sessionId}`

```
{
  sessionId: string,     // uuid4
  topic: string,
  difficulty: "easy" | "medium" | "hard",
  title: string,
  objective: string,
  questions: [
    { id: string, prompt: string, options: string[], concept: string }
  ],
  answerKey: { [questionId: string]: number },   // correct option index
  answers: { [questionId: string]: number },     // learner's chosen index
  score: number | null,          // percentage, set on submit
  incorrectConcepts: string[],
  timeSpentSeconds: number | null,
  completed: boolean,
  startedAt: timestamp,
  completedAt: timestamp | null
}
```

`answerKey` is written at session creation and never exposed to the UI
layer before submission — the correct answers exist only server-side
until the learner has answered.

### `users/{uid}/learningPaths/{pathId}` — Self-Learner, DEFERRED

Not created or read by any code path in this MVP. Kept here only because
it's part of the target end-state schema; do not implement (see PRD.md
Non-Goals / this doc's own "deferred" note).

## Queries

Only one multi-document query exists: `list_recent_sessions` —
`sessions` ordered by `completedAt` descending, filtered to `completed ==
True` **in Python after fetch**, not via a Firestore `.where()` clause.

This is deliberate: combining an equality filter with `order_by` on a
different field requires a Firestore composite index that doesn't exist
by default, and fails even against an empty collection. Single-field
`order_by` needs no composite index (Firestore auto-indexes every field),
so filtering client-side avoids that failure mode entirely. See
`src/services/firestore_service.py::list_recent_sessions` docstring.

No other composite indexes are required by this schema. If a future query
adds a second filter/order dimension, a composite index requirement must
be checked before shipping it.

## Fields referenced in this review but not yet in the schema

Per PRODUCT DECISIONS in this documentation round:

- **Grade** (performance classification) is *derived at read time* from
  `sessions/{sessionId}.score` — **not** planned as a stored field. See
  AI_SPEC.md / ACCEPTANCE_TESTS.md GRADE-001. Status: planned,
  implementation required.
- **Kinara Level** is *derived at read time* from
  `learningMemory/current.totalXP` — **not** planned as a stored field,
  to avoid a second source of truth that could drift from `totalXP`.
  Status: planned, implementation required.
- **Strike Status** (today-completed / badge) is *derived at read time*
  from `learningMemory/current.streak` + `.lastSessionAt` — no new field.
  Status: planned, implementation required.

Nothing above requires a schema change. Do not add stored `grade`,
`level`, or `strikeStatus` fields — compute them from existing data.
