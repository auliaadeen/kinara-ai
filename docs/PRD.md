# Kinara AI — Product Requirements Document

Version: 3.1
Status: LOCKED

## 1. Product

Kinara AI is an AI-powered adaptive learning companion.

Core promise (immutable):

"Kinara remembers learning behavior and adapts the next learning experience."

Kinara is not primarily an AI content generator.

Its core value is the continuous learning loop:

LEARN → TEST → SCORE → REMEMBER → ANALYZE → ADAPT → RECOMMENDED NEXT → LEARN AGAIN

(This elaborates the same loop as before — SCORE and ANALYZE are called
out as distinct steps because they're each a separate deterministic
Python responsibility, not folded into "Assess"/"Adapt". No behavior
change, just precision.)

## 2. Problem

Most AI learning tools can generate lessons from a prompt, but each interaction can become isolated.

The learner must repeatedly explain:

- who they are
- what they are learning
- what they struggled with
- what they already mastered
- what they should study next

Kinara solves this by maintaining Learning Memory.

## 3. Target Users

### Primary

Parent managing a child's learning journey.

### Secondary

Self-learner aged 18+. **Deferred for this MVP** — see §4.

## 4. Product Modes

### Parent-Child Workspace

Parents can:

- create child profiles
- select learning topics
- generate personalized learning experiences
- review results (Session Success / Results — UI_SPEC.md)
- see learning memory ("What Kinara Remembers")
- see performance Grade per session (planned — implementation required)
- see Kinara Level and progress (planned — implementation required)
- see streak / Strike Status (planned — implementation required)
- browse Exam History (planned — implementation required)
- continue learning via a working "Continue Learning" action (planned —
  implementation required; current CTA is a known no-op, see
  ACCEPTANCE_TESTS.md UI-002)

### Self-Learner — DEFERRED

Not implemented, not in scope for this MVP/submission. Kept here only as
the target end-state description:

- define a learning goal
- generate a learning path
- complete learning sessions
- receive assessment
- build learning memory
- receive adaptive next-step recommendations

## 5. Core Differentiator

Learning Memory.

Kinara stores measurable learning signals and uses them to influence future learning experiences.

Signals include:

- scores
- incorrect answers
- repeated mistakes
- completion
- attempts
- time spent
- topic history
- difficulty
- improvement trend
- streak

### 5.1 User-facing expressions of these signals (this MVP round)

Grade, Kinara Level, and Strike Status are not new signals — they are
deterministic, judge-legible expressions of signals already listed above
(Grade from score, Level from cumulative XP, Strike Status from streak).
See FSD.md for the exact rules and ACCEPTANCE_TESTS.md for pass criteria.

## 6. AI Responsibility

Gemini is responsible for:

- generating learning content (worksheets: title, objective, questions)
- generating explanations within that content
- summarizing learning evidence when appropriate (as prompt input framing, not as a decision)

Gemini is explicitly NOT responsible for (see AI_SPEC.md §0):

- deciding the next difficulty or topic
- generating the "Recommended Next" recommendation
- assigning Grade or Kinara Level
- calculating score or XP

Application logic (Python) is responsible for:

- authentication
- authorization
- persistence
- score calculation
- Grade calculation
- mastery calculation
- Kinara Level calculation
- XP calculation
- streak / Strike Status calculation
- memory retrieval
- adaptive rules (including the "Recommended Next" decision)
- validation

## 7. Google Cloud Requirements

The MVP must use:

- Google Cloud Run
- Firebase Authentication
- Cloud Firestore
- Gemini API / Google Gen AI SDK

## 8. MVP Success Criteria

A reviewer can:

1. Register/login.
2. Create a child profile.
3. Generate a learning activity.
4. Complete it.
5. Receive a score and a Grade (planned — implementation required).
6. See Learning Memory updated, including mastery/weak/strong concepts.
7. See Kinara Level and streak / Strike Status reflect the session
   (planned — implementation required).
8. Generate the next activity via "Continue Learning" (planned —
   implementation required — see §4).
9. Observe that the next activity reflects previous performance.
10. Browse Exam History and see progression over time (planned —
    implementation required).

Point 9 remains the single most important demonstration of Kinara's
value — everything else in this list supports making that demonstration
legible to a judge, not a substitute for it.
