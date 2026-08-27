# Kinara AI — Acceptance Tests

Version: 3.0

## AUTH-001

Given a new user

When they register

Then Firebase creates an authenticated account.

## AUTH-002

Given an authenticated parent

When they create a child

Then Firestore stores the child under their UID.

## SESSION-001

Given a child

When parent starts a learning session

Then Kinara loads the child's Learning Memory.

## SESSION-002

Given no previous learning history

When generating the first activity

Then Kinara generates a valid baseline learning experience.

## MEMORY-001

Given a completed session

When the session is submitted

Then score is calculated by the application.

## MEMORY-002

Given a completed session

Then Learning Memory is updated in Firestore.

## MEMORY-003

Given previous weak concepts

When generating the next session

Then weak concepts are included in the adaptive context.

## MEMORY-004

Given previous performance

When generating the next experience

Then difficulty/focus reflects previous performance.

## MEMORY-005

Given user logs out

When they log in again

Then Learning Memory persists.

## ADAPT-001

Score < 60%

Then recommended difficulty should decrease.

## ADAPT-002

Score 60-79%

Then recommended difficulty remains similar.

## ADAPT-003

Score >= 80%

Then recommended difficulty may increase.

## ADAPT-004

Given repeated mistakes

Then the repeated weak concept receives higher priority.

## AI-001

Gemini returns valid JSON

Then Pydantic validation succeeds.

## AI-002

Gemini returns invalid JSON

Then system retries once.

## AI-003

Gemini fails twice

Then system shows controlled error.

## SECURITY-001

User A

Cannot access User B's documents.

## DEPLOY-001

Application runs successfully on Cloud Run.

## DEMO-001 — CRITICAL

The following sequence must work:

1. Create learner.
2. Generate activity.
3. Complete activity.
4. Score is calculated.
5. Learning Memory updates.
6. Start next activity.
7. Next activity reflects previous weakness.

If DEMO-001 fails, MVP is not considered complete.