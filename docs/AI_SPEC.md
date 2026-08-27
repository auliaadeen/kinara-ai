# Kinara AI — AI Specification

## 1. Model

Use Google Gen AI SDK.

Default model should be configurable through environment variables.

Example:

GEMINI_MODEL=gemini-3.6-flash

Do not hard-code model selection throughout the codebase.

## 2. Structured Output

Gemini outputs must be JSON.

Every AI response must be validated using Pydantic.

Never blindly trust response.text.

## 3. Learning Experience Input

Gemini receives:

- learner profile
- educational level
- topic
- learning goal
- Learning Memory
- adaptive recommendation
- recent relevant sessions

## 4. Memory Principle

If historical learning data exists, the prompt MUST contain it.

Do not send:

"Create a worksheet about fractions."

Instead send contextual information:

Learner:
Grade 2

Previous performance:
60%, 72%

Weak concept:
Comparing fractions

Strong concept:
Identifying fractions

Trend:
Improving

Recommended difficulty:
Medium

## 5. AI Must Not

Gemini must not:

- calculate final score
- modify Firestore directly
- authenticate users
- assign arbitrary XP
- invent previous learning history
- claim a learner mastered something without evidence

## 6. AI Output

Worksheet:

{
  "title": "...",
  "objective": "...",
  "difficulty": "...",
  "questions": [...]
}

Recommendation:

{
  "topic": "...",
  "difficulty": "...",
  "objective": "...",
  "reason": "..."
}

## 7. Safety

For children:

- age-appropriate content
- no harmful content
- no collection of unnecessary sensitive information
- avoid requesting personal information from children

## 8. Retry

Invalid structured output:

Retry once.

Second failure:

Return controlled application error.