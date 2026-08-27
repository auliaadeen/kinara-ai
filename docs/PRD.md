# Kinara AI — Product Requirements Document

Version: 3.0
Status: LOCKED

## 1. Product

Kinara AI is an AI-powered adaptive learning companion.

Core promise:

"Kinara remembers learning behavior and adapts the next learning experience."

Kinara is not primarily an AI content generator.

Its core value is the continuous learning loop:

Learn → Assess → Remember → Adapt → Next Experience.

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

Self-learner aged 18+.

## 4. Product Modes

### Parent-Child Workspace

Parents can:

- create child profiles
- select learning topics
- generate personalized learning experiences
- review results
- see learning memory
- continue learning

### Self-Learner

Learners can:

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

## 6. AI Responsibility

Gemini is responsible for:

- generating learning content
- generating explanations
- generating recommendations
- summarizing learning evidence when appropriate

Application logic is responsible for:

- authentication
- authorization
- persistence
- score calculation
- mastery calculation
- XP calculation
- memory retrieval
- adaptive rules
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
5. Receive a score.
6. See Learning Memory updated.
7. Generate the next activity.
8. Observe that the next activity reflects previous performance.

The final point is the most important demonstration of Kinara's value.