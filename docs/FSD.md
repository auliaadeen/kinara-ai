# Kinara AI — Functional Specification Document

Version: 3.0
Status: LOCKED

## 1. Functional Principle

Kinara must implement this loop:

LEARN
→ ASSESS
→ REMEMBER
→ ADAPT
→ GENERATE
→ NEXT EXPERIENCE

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
- streak
- mastery overview
- weak concepts
- strong concepts
- recommended next activity

### 3.3 Generate Learning Experience

Input:

- childId
- topic
- optional difficulty

System:

1. Load child profile.
2. Load learning memory.
3. Load recent sessions.
4. Run adaptive engine.
5. Build Gemini prompt.
6. Request structured JSON.
7. Validate response.
8. Display learning activity.

If learning history exists, it MUST be included in the adaptive context.

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
- weakConcepts
- strongConcepts
- recentTopics
- difficulty
- learningTrend
- totalXP
- streak
- lastSessionAt

## 8. Adaptive Engine

The Adaptive Engine determines the next learning direction.

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

## 10. Self-Learner

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

## 12. Error Handling

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

## 13. Non-Goals

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