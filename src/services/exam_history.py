"""Exam History row assembly (FSD.md #13, ACCEPTANCE_TESTS.md HIST-001).

Turns a list of completed LearningSession docs (already persisted — no new
Firestore field, per DATA_MODEL.md/FIRESTORE_SCHEMA.md) into fully-derived
display rows: Grade (from score), a per-row trend label (vs. the
immediately preceding session), and the XP that session actually earned
(reconstructed deterministically — XP was never stored per-session, only
as a cumulative running total). Pure function, no I/O — the caller is
responsible for fetching UID-scoped sessions via FirestoreService.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.session import LearningSession
from src.services import gamification


@dataclass
class HistoryRow:
    session_id: str
    completed_at: datetime | None
    topic: str
    score: float
    grade_letter: str
    grade_label: str
    trend_label: str
    xp_earned: int
    status: str


def build_history_rows(sessions_newest_first: list[LearningSession]) -> list[HistoryRow]:
    """sessions_newest_first: as returned by FirestoreService.list_session_history
    (already completed-only, newest first). Returns rows in the same order."""
    oldest_first = list(reversed(sessions_newest_first))

    xp_series = gamification.reconstruct_session_xp_history(
        [(s.score or 0.0, s.completed_at) for s in oldest_first]
    )

    rows_oldest_first: list[HistoryRow] = []
    previous_score: float | None = None
    for session, xp in zip(oldest_first, xp_series):
        score = session.score or 0.0
        letter, label = gamification.compute_grade(score)
        trend_label = gamification.session_result_trend(previous_score, score)
        rows_oldest_first.append(
            HistoryRow(
                session_id=session.session_id,
                completed_at=session.completed_at,
                topic=session.topic,
                score=score,
                grade_letter=letter,
                grade_label=label,
                trend_label=trend_label,
                xp_earned=xp,
                status="Completed",
            )
        )
        previous_score = score

    return list(reversed(rows_oldest_first))
