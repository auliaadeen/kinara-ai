"""Learning Session orchestration — the DEMO-001 critical path.

Wires: adaptive engine -> Gemini -> Pydantic-validated content -> user
answers -> Python scoring -> Learning Memory update -> Firestore
persistence -> next recommendation. This module is intentionally the only
place that calls every other service, so the full loop (FSD.md #1) is easy
to read start to finish.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from src.config import Settings
from src.models.common import Difficulty
from src.models.learning_memory import LearningMemory
from src.models.session import LearningSession, QuestionRecord
from src.services import adaptive_engine, ai_engine, gamification
from src.services.firestore_service import FirestoreService
from src.utils.concepts import normalize_concept

RECENT_SESSIONS_FOR_CONTEXT = 3
MAX_RECENT_TOPICS = 5


class ChildNotFoundError(RuntimeError):
    pass


@dataclass
class SubmitResult:
    score: float
    xp_awarded: int
    xp_breakdown: dict[str, int]
    memory: LearningMemory
    next_experience: adaptive_engine.NextExperience


def generate_learning_experience(
    settings: Settings,
    fs: FirestoreService,
    child_id: str,
    topic: str,
    difficulty_override: Difficulty | None,
) -> LearningSession:
    child = fs.get_child(child_id)
    if child is None:
        raise ChildNotFoundError("Child profile not found.")

    memory = fs.get_learning_memory(child_id)
    recent_sessions = fs.list_recent_sessions(child_id, limit=RECENT_SESSIONS_FOR_CONTEXT)
    recent_scores = [s.score for s in reversed(recent_sessions) if s.score is not None]

    context = adaptive_engine.build_generation_context(memory, difficulty_override)
    prompt = ai_engine.build_worksheet_prompt(child, memory, context, topic, recent_scores)
    worksheet = ai_engine.generate_worksheet(settings, prompt)

    questions: list[QuestionRecord] = []
    answer_key: dict[str, int] = {}
    for gen_q in worksheet.questions:
        qid = str(uuid.uuid4())
        questions.append(
            QuestionRecord(
                id=qid,
                prompt=gen_q.prompt,
                options=gen_q.options,
                concept=normalize_concept(gen_q.concept),
            )
        )
        answer_key[qid] = gen_q.correct_answer_index

    session = LearningSession(
        session_id=str(uuid.uuid4()),
        topic=topic,
        difficulty=worksheet.difficulty,
        title=worksheet.title,
        objective=worksheet.objective,
        questions=questions,
        answer_key=answer_key,
    )
    fs.create_session(child_id, session)
    return session


def submit_learning_session(
    fs: FirestoreService,
    child_id: str,
    session: LearningSession,
    answers: dict[str, int],
    time_spent_seconds: int,
) -> SubmitResult:
    concept_by_question = {q.id: q.concept for q in session.questions}
    score = gamification.calculate_score(answers, session.answer_key)
    wrong_concepts = gamification.incorrect_concepts(answers, session.answer_key, concept_by_question)

    memory = fs.get_learning_memory(child_id)
    recent_sessions = fs.list_recent_sessions(child_id, limit=RECENT_SESSIONS_FOR_CONTEXT)
    recent_scores = [s.score for s in recent_sessions if s.score is not None]

    now = datetime.now(timezone.utc)
    new_streak, streak_incremented = gamification.compute_streak(
        memory.streak, memory.last_session_at, now
    )
    trend = gamification.compute_trend(recent_scores, score)
    improved = trend == "improving"
    xp_awarded, xp_breakdown = gamification.compute_xp(
        completed=True, score=score, improved=improved, streak_incremented=streak_incremented
    )

    concept_correctness: dict[str, bool] = {}
    for q in session.questions:
        correct = answers.get(q.id) == session.answer_key.get(q.id)
        concept_correctness[q.concept] = concept_correctness.get(q.concept, True) and correct
    updated_history = gamification.update_concept_history(memory.concept_history, concept_correctness)
    updated_mastery = gamification.compute_mastery_map(updated_history)
    weak, strong = gamification.derive_weak_strong(updated_mastery)

    recent_topics = [session.topic] + [t for t in memory.recent_topics if t != session.topic]
    recent_topics = recent_topics[:MAX_RECENT_TOPICS]

    next_diff = adaptive_engine.next_difficulty(session.difficulty, score)
    new_total_xp = memory.total_xp + xp_awarded

    new_memory = LearningMemory(
        mastery_map=updated_mastery,
        concept_history=updated_history,
        weak_concepts=weak,
        strong_concepts=strong,
        recent_topics=recent_topics,
        recommended_difficulty=next_diff,
        learning_trend=trend,
        total_xp=new_total_xp,
        streak=new_streak,
        last_session_at=now,
        updated_at=now,
    )

    session.answers = answers
    session.score = score
    session.incorrect_concepts = wrong_concepts
    session.time_spent_seconds = time_spent_seconds
    session.completed = True
    session.completed_at = now

    fs.complete_session(child_id, session)
    fs.save_learning_memory(child_id, new_memory)
    fs.update_child_xp_streak(child_id, new_total_xp, new_streak)

    repeated_weak = adaptive_engine.priority_weak_concept(memory.weak_concepts, wrong_concepts)
    next_experience = adaptive_engine.build_next_experience(
        updated_memory=new_memory, last_topic=session.topic, repeated_weak_concept=repeated_weak
    )

    return SubmitResult(
        score=score,
        xp_awarded=xp_awarded,
        xp_breakdown=xp_breakdown,
        memory=new_memory,
        next_experience=next_experience,
    )
