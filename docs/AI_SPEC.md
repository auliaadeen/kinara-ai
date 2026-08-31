# Kinara AI — AI Specification

Version: 3.1

## 0. Architecture Boundary (explicit)

Gemini generates learning **content only** — worksheet title, objective,
questions, options, and per-question concept tags. Gemini never decides:

- the learner's next difficulty
- the learner's next topic
- whether a concept is weak/strong/mastered
- XP, score, streak, or Level
- what to recommend next and why

All of the above are 100% deterministic Python
(`src/services/adaptive_engine.py`, `src/services/gamification.py`).
Gemini is *told* the already-decided difficulty and focus concepts as
input context (§3/§4 below) — it does not derive them. Do not claim, in
any submission material, that Gemini performs the adaptive decision; it
generates worksheets from a decision Python already made.

This is unchanged behavior — it documents what `src/services/ai_engine.py`
and `src/services/adaptive_engine.py` already do — not a new rule.

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
- decide the next difficulty or topic (§0)
- assign a Grade or Kinara Level
- modify Firestore directly
- authenticate users
- assign arbitrary XP
- invent previous learning history
- claim a learner mastered something without evidence

## 6. AI Output

Worksheet (the only structured output requested from Gemini):

{
  "title": "...",
  "objective": "...",
  "difficulty": "...",
  "questions": [
    { "id", "prompt", "options", "correct_answer_index", "concept" }
  ]
}

Validated against `WorksheetResponse` (`src/models/ai_schemas.py`) via
`response_schema` + independent Pydantic re-validation (§2).

**Recommendation is NOT a Gemini output.** The "Recommended Next"
topic/difficulty/objective/reason shown to the user (FSD.md "Next
Experience") is built entirely by
`adaptive_engine.build_next_experience` from stored Learning Memory
evidence — no Gemini call. An earlier draft of this spec showed a
"Recommendation" JSON block as if Gemini produced it; that was corrected
to match the actual implementation, which deliberately keeps this
decision out of the model (§0, and AI_SPEC.md §5's "must not invent
previous learning history" — a recommendation Gemini generated itself
could not be evidence-grounded the way a Python calculation over stored
history can).

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