"""Deterministic scoring, XP, mastery and streak rules.

ARCHITECTURE.md #3: Python is the source of truth for score/XP/mastery, never
Gemini. FSD.md #5: score is calculated by the application, not by the model.
FSD.md #11: XP is deterministic, never random.

All functions here are pure (no I/O) so they're directly unit-testable
(AI_RULES Rule 8).
"""
from __future__ import annotations

from datetime import date, datetime
from statistics import mean

from src.models.common import LearningTrend

COMPLETION_XP = 10
HIGH_SCORE_XP = 10
HIGH_SCORE_THRESHOLD = 80.0
IMPROVEMENT_XP = 5
STREAK_XP = 5

WEAK_THRESHOLD = 50.0
STRONG_THRESHOLD = 80.0
NEUTRAL_MASTERY = 50.0

# History-aware mastery: each concept keeps a short rolling window of its
# most recent correct/incorrect outcomes. Older attempts count less than
# newer ones (linear recency weights), and a fixed-weight neutral prior is
# always mixed in so a single attempt — good or bad — can never instantly
# swing a concept between weak/improving/strong on its own; sustained
# recent performance is what moves it (and can move it back).
CONCEPT_HISTORY_WINDOW = 5
NEUTRAL_PRIOR_WEIGHT = 1.0

TREND_MARGIN = 5.0


def calculate_score(answers: dict[str, int], answer_key: dict[str, int]) -> float:
    """FSD.md #5: scorePercentage = correctAnswers / totalQuestions * 100."""
    total = len(answer_key)
    if total == 0:
        return 0.0
    correct = sum(1 for qid, correct_idx in answer_key.items() if answers.get(qid) == correct_idx)
    return round(correct / total * 100, 2)


def incorrect_concepts(
    answers: dict[str, int], answer_key: dict[str, int], concept_by_question: dict[str, str]
) -> list[str]:
    concepts: list[str] = []
    for qid, correct_idx in answer_key.items():
        if answers.get(qid) != correct_idx:
            concept = concept_by_question.get(qid)
            if concept and concept not in concepts:
                concepts.append(concept)
    return concepts


def compute_streak(previous_streak: int, last_session_at: datetime | None, now: datetime) -> tuple[int, bool]:
    """Calendar-day based streak. Same calendar day = no change. Next
    consecutive calendar day = +1. Any gap = reset to 1."""
    today: date = now.date()
    if last_session_at is None:
        return 1, True
    last_day = last_session_at.date()
    if today == last_day:
        return previous_streak, False
    if (today - last_day).days == 1:
        return previous_streak + 1, True
    return 1, True


def compute_trend(recent_scores: list[float], new_score: float) -> LearningTrend:
    if not recent_scores:
        return "stable"
    avg_prev = mean(recent_scores)
    if new_score > avg_prev + TREND_MARGIN:
        return "improving"
    if new_score < avg_prev - TREND_MARGIN:
        return "declining"
    return "stable"


def compute_xp(*, completed: bool, score: float, improved: bool, streak_incremented: bool) -> tuple[int, dict[str, int]]:
    breakdown: dict[str, int] = {}
    if completed:
        breakdown["completion"] = COMPLETION_XP
    if score >= HIGH_SCORE_THRESHOLD:
        breakdown["high_score"] = HIGH_SCORE_XP
    if improved:
        breakdown["improvement"] = IMPROVEMENT_XP
    if streak_incremented:
        breakdown["streak"] = STREAK_XP
    return sum(breakdown.values()), breakdown


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def update_concept_history(
    concept_history: dict[str, list[bool]], concept_correctness: dict[str, bool]
) -> dict[str, list[bool]]:
    """Append this session's outcome for each concept touched, oldest first,
    trimmed to the last CONCEPT_HISTORY_WINDOW attempts.

    concept_correctness: normalized concept slug -> whether it was answered
    correctly in this session (a concept can appear more than once; any
    incorrect occurrence counts as incorrect for that concept this round).
    Works for any concept slug — nothing here is topic- or concept-specific.
    """
    updated = {concept: list(history) for concept, history in concept_history.items()}
    for concept, correct in concept_correctness.items():
        history = updated.get(concept, [])
        history.append(correct)
        updated[concept] = history[-CONCEPT_HISTORY_WINDOW:]
    return updated


def concept_mastery_score(history: list[bool]) -> float:
    """Recency-weighted mastery score in 0..100 for one concept's outcome
    history (oldest first). A fixed-weight neutral (50) prior is blended in
    so a single result never fully overrides an empty or short history, and
    linearly increasing weights (oldest=1 .. newest=len(history)) mean the
    most recent attempts matter most — sustained recent correctness pulls
    the score up toward 100, sustained recent misses pull it down toward 0,
    and the rolling window means old evidence eventually ages out, allowing
    regression as well as progression."""
    if not history:
        return NEUTRAL_MASTERY
    weights = list(range(1, len(history) + 1))
    weighted_sum = sum(w * (100.0 if correct else 0.0) for w, correct in zip(weights, history))
    total_weight = sum(weights) + NEUTRAL_PRIOR_WEIGHT
    score = (weighted_sum + NEUTRAL_PRIOR_WEIGHT * NEUTRAL_MASTERY) / total_weight
    return round(_clamp(score), 1)


def compute_mastery_map(concept_history: dict[str, list[bool]]) -> dict[str, float]:
    return {concept: concept_mastery_score(history) for concept, history in concept_history.items()}


def concept_state(score: float) -> str:
    """One of "weak", "improving", "strong" (a.k.a. mastered) — the state a
    concept moves through as evidence accumulates (weak -> improving ->
    strong), and can move back through if recent performance regresses."""
    if score >= STRONG_THRESHOLD:
        return "strong"
    if score < WEAK_THRESHOLD:
        return "weak"
    return "improving"


def derive_weak_strong(mastery_map: dict[str, float]) -> tuple[list[str], list[str]]:
    weak = sorted([c for c, v in mastery_map.items() if concept_state(v) == "weak"])
    strong = sorted([c for c, v in mastery_map.items() if concept_state(v) == "strong"])
    return weak, strong
