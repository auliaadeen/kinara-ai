# Kinara AI — Data Model

Version: 3.1
Status: LOCKED (overview). For exact types and implementation detail, see
docs/FIRESTORE_SCHEMA.md — that document is canonical; this one is the
human-readable summary and must not contradict it.

## users/{uid}

{
  uid,
  email,
  role,
  createdAt
}

## users/{uid}/children/{childId}

{
  childId,
  name,
  educationalLevel,   ← school grade (e.g. "Grade 3"). NOT the same
                         concept as performance Grade — see below.
  preferredLearningStyle,
  xp,
  streak,
  createdAt,
  updatedAt
}

## users/{uid}/children/{childId}/learningMemory/current

{
  masteryMap,
  conceptHistory,
  weakConcepts,
  strongConcepts,
  recentTopics,
  recommendedDifficulty,
  learningTrend,
  totalXP,
  streak,
  lastSessionAt,
  updatedAt
}

### conceptHistory (added this round)

`{ [conceptSlug]: boolean[] }` — the last 5 correct/incorrect outcomes
for each concept, oldest first. This is the source of truth `masteryMap`
is computed from; `masteryMap` is a derived cache, not independently
authoritative.

**Why it exists:** a single flat +/- step per session couldn't recover a
concept from a low mastery value in one session, so a genuinely-mastered
concept could stay classified "weak" forever after just a couple of bad
early attempts. `conceptHistory` lets mastery be a recency-weighted score
over a short window instead of one memoryless number — a concept now
moves weak → improving → strong as evidence accumulates, and can regress
if recent performance drops. See `src/services/gamification.py` for the
exact formula (`concept_mastery_score`, `concept_state`).

**Relationship to masteryMap:** every session, `conceptHistory` is
updated first (append this session's outcome per concept, trim to last
5), then `masteryMap` is fully recomputed from it
(`compute_mastery_map`). `weakConcepts`/`strongConcepts` are then derived
from `masteryMap` by threshold, unchanged from before. Both fields are
persisted together — `masteryMap` is kept only so the dashboard and
`weakConcepts`/`strongConcepts` derivation don't need to recompute the
weighted formula on every read.

## users/{uid}/children/{childId}/sessions/{sessionId}

{
  sessionId,
  topic,
  difficulty,
  title,
  objective,
  questions,
  answerKey,
  answers,
  score,
  incorrectConcepts,
  timeSpentSeconds,
  completed,
  startedAt,
  completedAt
}

`title`/`objective` were already implemented but missing from this doc
previously — added here to match `src/models/session.py`.

## Grade, Kinara Level, Strike Status — NOT stored fields

These three concepts (added to MVP scope this round — see PRD.md,
FSD.md) are **computed at read time**, not persisted:

- **Grade** — derived from `sessions/{sessionId}.score` (per session).
- **Kinara Level** — derived from `learningMemory/current.totalXP`
  (cumulative, per child).
- **Strike Status** — derived from `learningMemory/current.streak` +
  `.lastSessionAt` (per child).

Deriving instead of storing avoids a second source of truth that could
drift from `score`/`totalXP`/`streak`. Do not add `grade`, `level`, or
`strikeStatus` fields to any document. Status: planned, implementation
required (see ACCEPTANCE_TESTS.md GRADE-001, LEVEL-001, STREAK-001).

## users/{uid}/learningPaths/{pathId} — Self-Learner, DEFERRED

{
  pathId,
  targetGoal,
  durationDays,
  modules,
  progressPercentage,
  createdAt
}

Not created or read by any code in this MVP. Self-Learner remains out of
scope for this submission (PRD.md, FSD.md).

## Design Rule

All user-owned documents must be scoped by Firebase UID.

Never query another user's documents.

Never trust client-provided UID.
