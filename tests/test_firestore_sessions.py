"""list_recent_sessions must not need a Firestore composite index, and must
only surface completed sessions (MEMORY-003/MEMORY-004 depend on this: the
next generation's adaptive context is built from these results)."""
from datetime import datetime, timezone, timedelta

from tests.fakes.fake_firestore import FakeFirestoreClient

from src.models.session import LearningSession
from src.services.firestore_service import FirestoreService

UID = "user-a"
CHILD_ID = "child-1"


def _session(session_id: str, completed: bool, completed_at: datetime | None) -> LearningSession:
    return LearningSession(
        session_id=session_id,
        topic="Fractions",
        difficulty="easy",
        title="Fractions Basics",
        objective="Identify fractions",
        questions=[],
        answer_key={},
        completed=completed,
        completed_at=completed_at,
        score=80.0 if completed else None,
    )


def test_returns_only_completed_sessions():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, UID)
    now = datetime.now(timezone.utc)

    # Firestore returns docs pre-sorted by completedAt DESC; the fake
    # preserves insertion order, so insert in that already-sorted order.
    fs.create_session(CHILD_ID, _session("s1", completed=True, completed_at=now))
    fs.create_session(CHILD_ID, _session("s2-in-progress", completed=False, completed_at=None))
    fs.create_session(CHILD_ID, _session("s3", completed=True, completed_at=now - timedelta(days=1)))

    result = fs.list_recent_sessions(CHILD_ID, limit=5)

    assert [s.session_id for s in result] == ["s1", "s3"]
    assert all(s.completed for s in result)


def test_respects_limit():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, UID)
    now = datetime.now(timezone.utc)

    for i in range(5):
        fs.create_session(
            CHILD_ID, _session(f"s{i}", completed=True, completed_at=now - timedelta(days=i))
        )

    result = fs.list_recent_sessions(CHILD_ID, limit=3)

    assert len(result) == 3


def test_empty_sessions_subcollection_returns_empty_list_not_error():
    db = FakeFirestoreClient()
    fs = FirestoreService(db, UID)

    result = fs.list_recent_sessions(CHILD_ID, limit=3)

    assert result == []


def test_query_shape_has_no_equality_filter_needing_composite_index():
    """Regression guard: a where("completed", "==", True) combined with
    order_by("completedAt") needs a Firestore composite index that doesn't
    exist by default, and fails even on an empty collection. Assert the
    query built here never calls .where(...) at all."""
    calls = []

    class RecordingCollection:
        def where(self, *a, **k):
            calls.append(("where", a, k))
            return self

        def order_by(self, *a, **k):
            calls.append(("order_by", a, k))
            return self

        def limit(self, *a, **k):
            calls.append(("limit", a, k))
            return self

        def stream(self):
            return iter([])

    class ChainNode:
        """Stands in for every intermediate users/{uid}/children/{id} ref —
        only the terminal 'sessions' collection needs to record calls."""

        def collection(self, name):
            return RecordingCollection() if name == "sessions" else ChainNode()

        def document(self, doc_id):
            return ChainNode()

    class RecordingDB:
        def collection(self, name):
            return ChainNode()

    fs = FirestoreService(RecordingDB(), UID)
    fs.list_recent_sessions(CHILD_ID, limit=3)

    assert not any(call[0] == "where" for call in calls), (
        "list_recent_sessions must not use an equality where() combined with "
        "order_by() — that query shape needs a composite index that doesn't "
        "exist by default and fails even on an empty collection"
    )
