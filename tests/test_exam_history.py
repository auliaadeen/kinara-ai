"""HIST-001 — Exam History.

Two layers: exam_history.build_history_rows (pure row-shaping — grade,
trend, XP derivation) and FirestoreService.list_session_history (fetch,
newest-first, UID-scoped, no separate collection).
"""
from datetime import datetime, timedelta, timezone

from tests.fakes.fake_firestore import FakeFirestoreClient

from src.models.session import LearningSession
from src.services import exam_history
from src.services.firestore_service import FirestoreService

CHILD_ID = "child-1"


def _session(session_id: str, score: float, completed_at: datetime, topic: str = "Fractions") -> LearningSession:
    return LearningSession(
        session_id=session_id,
        topic=topic,
        difficulty="easy",
        title="Worksheet",
        objective="Practice",
        questions=[],
        answer_key={},
        completed=True,
        completed_at=completed_at,
        score=score,
    )


# --- build_history_rows (pure) ------------------------------------------------


def test_build_history_rows_empty():
    assert exam_history.build_history_rows([]) == []


def test_build_history_rows_single_session_no_previous_trend():
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    rows = exam_history.build_history_rows([_session("s1", 80.0, now)])
    assert len(rows) == 1
    assert rows[0].trend_label == "—"
    assert rows[0].grade_letter == "A"


def test_build_history_rows_grade_derivation_matches_gamification():
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    rows = exam_history.build_history_rows([_session("s1", 55.0, now)])
    assert (rows[0].grade_letter, rows[0].grade_label) == ("C", "Fair")


def test_build_history_rows_preserves_newest_first_order():
    d1 = datetime(2026, 8, 25, 9, tzinfo=timezone.utc)
    d2 = datetime(2026, 8, 26, 9, tzinfo=timezone.utc)
    d3 = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    newest_first = [_session("s3", 90, d3), _session("s2", 70, d2), _session("s1", 50, d1)]

    rows = exam_history.build_history_rows(newest_first)

    assert [r.session_id for r in rows] == ["s3", "s2", "s1"]


def test_build_history_rows_trend_labels_compare_to_immediately_prior():
    d1 = datetime(2026, 8, 25, 9, tzinfo=timezone.utc)
    d2 = datetime(2026, 8, 26, 9, tzinfo=timezone.utc)
    d3 = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    # chronological: s1(50) -> s2(90, improved) -> s3(60, declined)
    newest_first = [_session("s3", 60, d3), _session("s2", 90, d2), _session("s1", 50, d1)]

    rows = exam_history.build_history_rows(newest_first)
    by_id = {r.session_id: r for r in rows}

    assert by_id["s1"].trend_label == "—"
    assert by_id["s2"].trend_label == "Improved"
    assert by_id["s3"].trend_label == "Declined"


def test_build_history_rows_status_is_completed():
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    rows = exam_history.build_history_rows([_session("s1", 80.0, now)])
    assert rows[0].status == "Completed"


def test_build_history_rows_xp_earned_is_non_negative_int():
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    rows = exam_history.build_history_rows([_session("s1", 80.0, now)])
    assert isinstance(rows[0].xp_earned, int)
    assert rows[0].xp_earned >= 0


# --- FirestoreService.list_session_history ------------------------------------


def test_list_session_history_empty():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, "user-a")
    assert fs.list_session_history(CHILD_ID) == []


def test_list_session_history_one_session():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, "user-a")
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    fs.create_session(CHILD_ID, _session("s1", 80.0, now))

    result = fs.list_session_history(CHILD_ID)

    assert [s.session_id for s in result] == ["s1"]


def test_list_session_history_multiple_sessions_newest_first():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, "user-a")
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    # Firestore returns docs pre-sorted by completedAt DESC; the fake
    # preserves insertion order, so insert already in that sorted order
    # (same convention as test_firestore_sessions.py).
    fs.create_session(CHILD_ID, _session("s3", 90, now))
    fs.create_session(CHILD_ID, _session("s2", 70, now - timedelta(days=1)))
    fs.create_session(CHILD_ID, _session("s1", 50, now - timedelta(days=2)))

    result = fs.list_session_history(CHILD_ID)

    assert [s.session_id for s in result] == ["s3", "s2", "s1"]


def test_list_session_history_excludes_incomplete_sessions():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, "user-a")
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    fs.create_session(CHILD_ID, _session("s1", 80.0, now))
    in_progress = LearningSession(
        session_id="s2-in-progress", topic="Fractions", difficulty="easy",
        title="W", objective="O", questions=[], answer_key={}, completed=False,
    )
    fs.create_session(CHILD_ID, in_progress)

    result = fs.list_session_history(CHILD_ID)

    assert [s.session_id for s in result] == ["s1"]


def test_list_session_history_uid_isolation():
    db = FakeFirestoreClient()
    fs_a = FirestoreService(db, "user-a")
    fs_b = FirestoreService(db, "user-b")
    now = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    fs_a.create_session(CHILD_ID, _session("s1", 80.0, now))

    assert len(fs_a.list_session_history(CHILD_ID)) == 1
    assert len(fs_b.list_session_history(CHILD_ID)) == 0
