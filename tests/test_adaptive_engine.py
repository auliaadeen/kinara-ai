from src.models.learning_memory import LearningMemory
from src.services import adaptive_engine


def test_build_generation_context_no_history_defaults_easy():
    memory = LearningMemory()
    ctx = adaptive_engine.build_generation_context(memory, requested_difficulty=None)
    assert ctx.difficulty == "easy"
    assert ctx.has_history is False
    assert ctx.focus_concepts == []


def test_build_generation_context_uses_memory_when_no_override():
    memory = LearningMemory(recommended_difficulty="hard", weak_concepts=["fractions"])
    ctx = adaptive_engine.build_generation_context(memory, requested_difficulty=None)
    assert ctx.difficulty == "hard"
    assert ctx.focus_concepts == ["fractions"]


def test_build_generation_context_explicit_override_wins():
    memory = LearningMemory(recommended_difficulty="hard")
    ctx = adaptive_engine.build_generation_context(memory, requested_difficulty="easy")
    assert ctx.difficulty == "easy"


def test_next_difficulty_low_score_decreases():
    assert adaptive_engine.next_difficulty("medium", 40) == "easy"


def test_next_difficulty_mid_score_stays_same():
    assert adaptive_engine.next_difficulty("medium", 70) == "medium"


def test_next_difficulty_high_score_increases():
    assert adaptive_engine.next_difficulty("medium", 90) == "hard"


def test_next_difficulty_clamped_at_floor():
    assert adaptive_engine.next_difficulty("easy", 10) == "easy"


def test_next_difficulty_clamped_at_ceiling():
    assert adaptive_engine.next_difficulty("hard", 95) == "hard"


def test_priority_weak_concept_repeated_miss():
    result = adaptive_engine.priority_weak_concept(["fractions", "addition"], ["subtraction", "fractions"])
    assert result == "fractions"


def test_priority_weak_concept_no_repeat():
    assert adaptive_engine.priority_weak_concept(["fractions"], ["subtraction"]) is None


def test_build_next_experience_repeated_weak_concept_takes_priority():
    memory = LearningMemory(recommended_difficulty="easy", weak_concepts=["fractions"], learning_trend="declining")
    exp = adaptive_engine.build_next_experience(
        updated_memory=memory, last_topic="Fractions", repeated_weak_concept="fractions"
    )
    assert "again" in exp.reason
    assert exp.difficulty == "easy"


def test_build_next_experience_progression_when_no_weak_concepts():
    memory = LearningMemory(recommended_difficulty="hard", weak_concepts=[], learning_trend="improving")
    exp = adaptive_engine.build_next_experience(
        updated_memory=memory, last_topic="Fractions", repeated_weak_concept=None
    )
    assert exp.difficulty == "hard"
    assert "increasing the challenge" in exp.reason
