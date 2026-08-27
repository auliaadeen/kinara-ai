# Kinara AI — AI Coding Rules

Version: 3.0
Status: LOCKED

## RULE 1 — Read Before Coding

Before modifying code, read:

docs/PRD.md
docs/FSD.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/AI_SPEC.md
docs/UI_SPEC.md
docs/SECURITY.md
docs/ACCEPTANCE_TESTS.md

## RULE 2 — Product Principle

Everything must support:

"AI remembers learning behavior and adapts the next learning experience."

## RULE 3 — Do Not Over-Engineer

Do not introduce:

- microservices
- unnecessary abstractions
- unnecessary frameworks
- vector databases
- agents
- queues
- Redis
- Cloud SQL

unless explicitly required.

## RULE 4 — Google Cloud Requirements

The application must genuinely use:

Cloud Run
Firebase Auth
Firestore
Gemini

Do not fake these integrations in the production implementation.

## RULE 5 — Source of Truth

Firestore:
persistent user/learning data.

Python:
business logic and deterministic calculations.

Gemini:
AI-generated content.

## RULE 6 — Never Fake Success

Do not show:

"Saved successfully"

unless Firestore write actually succeeds.

Do not show:

"AI generated"

unless Gemini successfully generated and validation succeeded.

## RULE 7 — Learning Memory

Whenever learning history exists, the AI generation pipeline MUST use relevant Learning Memory.

## RULE 8 — Testing

Write/update tests for business logic.

Prioritize:

- memory
- adaptation
- scoring
- gamification
- authorization

## RULE 9 — Small Changes

Implement incrementally.

After each major module:

run tests.

## RULE 10 — MVP Priority

Priority:

P0 Authentication
P0 Firestore
P0 Gemini
P0 Learning Session
P0 Learning Memory
P0 Adaptive Engine
P0 Demo Flow

P1 Gamification
P1 Analytics
P1 UI polish

P2 Everything else.

## RULE 11 — Do Not Expand Scope

If a feature is not required by PRD/FSD/Acceptance Tests:

do not implement it without explicit approval.

## RULE 12 — Explain Blockers

If an external configuration is missing:

stop at the boundary,
explain the required configuration,
do not silently replace production integration with a fake implementation.

## RULE 13 — Code Quality

Prefer:

simple
readable
typed
testable
modular

over:

clever
abstract
over-engineered