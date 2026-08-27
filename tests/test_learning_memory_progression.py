"""Reproduces the reported E2E bug: a concept that was weak before the
latest session stayed classified "weak" even after a 100% session, and the
"Kinara learned" recommendation kept citing it — because mastery used to be
a single flat +/-step per session, which can't escape a sufficiently low
value in one shot, and the recommendation must reflect whatever the memory
says *after* that update, not before.

These exercise the real session_service.submit_learning_session path (not
just the pure gamification functions) against the fake Firestore, so both
the algorithm and the "recommendation consumes updated memory" wiring are
covered together.
"""
from datetime import datetime, timedelta, timezone

from tests.fakes.fake_firestore import FakeFirestoreClient

from src.services import adaptive_engine, session_service
from src.services.firestore_service import FirestoreService
from src.models.session import LearningSession, QuestionRecord

UID = "user-a"
CHILD_ID = "child-1"
CONCEPT = "fractions_comparison"  # arbitrary — the algorithm must not special-case it


def _make_session(session_id: str, num_questions: int = 4) -> LearningSession:
    questions = [
        QuestionRecord(id=f"{session_id}-q{i}", prompt=f"Question {i}", options=["a", "b"], concept=CONCEPT)
        for i in range(num_questions)
    ]
    answer_key = {q.id: 0 for q in questions}
    return LearningSession(
        session_id=session_id,
        topic="Fractions",
        difficulty="easy",
        title="Fractions practice",
        objective="Practice fractions",
        questions=questions,
        answer_key=answer_key,
    )


def _submit(fs: FirestoreService, session_id: str, all_correct: bool):
    session = _make_session(session_id)
    fs.create_session(CHILD_ID, session)
    answers = {q.id: (0 if all_correct else 1) for q in session.questions}
    return session_service.submit_learning_session(fs, CHILD_ID, session, answers, time_spent_seconds=60)


def test_bug_repro_hundred_percent_session_lifts_previously_weak_concept():
    """Before: 2 poor sessions established CONCEPT as weak (matches the
    reported "pembilang dan penyebut" state). Latest: a 100% session on
    that same concept. It must no longer be reported as weak afterward."""
    db = FakeFirestoreClient()
    fs = FirestoreService(db, UID)
    fs.create_child("Test Child", "Grade 2", None)

    _submit(fs, "s1", all_correct=False)
    result_before = _submit(fs, "s2", all_correct=False)
    assert CONCEPT in result_before.memory.weak_concepts

    result_after = _submit(fs, "s3", all_correct=True)

    assert result_after.score == 100.0
    assert CONCEPT not in result_after.memory.weak_concepts, (
        "concept must move out of 'weak' after a 100% session, not stay "
        "permanently weak from earlier poor performance"
    )
    before_score = result_before.memory.mastery_map[CONCEPT]
    after_score = result_after.memory.mastery_map[CONCEPT]
    assert after_score > before_score


def test_recommendation_changes_when_weakness_changes():
    """The 'Kinara learned' reasoning must be built from the memory *after*
    this session's update, not the memory the session started with."""
    db = FakeFirestoreClient()
    fs = FirestoreService(db, UID)
    fs.create_child("Test Child", "Grade 2", None)

    _submit(fs, "s1", all_correct=False)
    result_before = _submit(fs, "s2", all_correct=False)
    reason_before = adaptive_engine.build_next_experience(
        updated_memory=result_before.memory, last_topic="Fractions", repeated_weak_concept=None
    ).reason
    assert CONCEPT.replace("_", " ") in reason_before

    result_after = _submit(fs, "s3", all_correct=True)
    reason_after = result_after.next_experience.reason

    assert reason_after != reason_before
    assert "remains a weak concept" not in reason_after or CONCEPT.replace("_", " ") not in reason_after
