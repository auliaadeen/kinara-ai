# Kinara AI — UI Specification

Version: 3.1

## Design Goal

The UI must make the adaptive loop visible.

The user should understand:

"What Kinara remembered"
and
"Why Kinara recommended this next."

## Parent Dashboard

Top:

Kinara AI
Child selector

Cards:

XP
Kinara Level (planned — implementation required, see FSD.md §11.2)
Streak / Strike Status badge (planned — implementation required, FSD.md §11.3)
Mastery
Learning Trend

Section:

## 🧠 What Kinara Remembers

Weak concepts
Strong concepts
Recent topics

Section:

## 🎯 Recommended Next

Topic
Difficulty
Reason

CTA:

Continue Learning — **must** trigger the next learning session directly
using this section's topic/difficulty (FSD.md §3.4). Currently a no-op;
this is the one CTA on the dashboard flagged as a defect
(ACCEPTANCE_TESTS.md UI-002).

Section (planned — implementation required):

## 🗂️ Exam History

A list of past completed sessions (FSD.md §13), most recent first. Each
row: date/time, topic, score, Grade, XP earned, status. Additive section
only — does not replace or restructure the sections above it.

## Session Success / Results

(Official name for this screen. Previously referred to informally as
just "Session" — same screen, name clarified for consistency across
docs and any judge-facing material.)

Show (during the session, before submit):

Title
Objective
Difficulty
Questions

After submit, show:

Score
Grade (planned — implementation required, FSD.md §5.1)
Correct/incorrect
XP earned
Improvement / learning trend
Memory updated (mastery/progression movement, where appropriate)

Then:

## 🧠 Kinara learned

Example:

"You need more practice comparing fractions."

CTA:

Practice Again — re-enters the generate flow for the same topic
(unchanged, already implemented).

Continue Learning — same behavior as the dashboard CTA (FSD.md §3.4):
must go directly to the next recommended session, not just back to the
dashboard. (planned — implementation required)

## Self-Learner — DEFERRED, not implemented

Kept as target end-state description only. Do not build for this MVP.

Show:

Goal
Current progress
Today's mission
Mastery
Learning memory
Next recommendation
