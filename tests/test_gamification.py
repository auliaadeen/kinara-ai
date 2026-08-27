from datetime import datetime, timezone

from src.services import gamification


def test_calculate_score_all_correct():
    assert gamification.calculate_score({"q1": 0, "q2": 1}, {"q1": 0, "q2": 1}) == 100.0


def test_calculate_score_partial():
    assert gamification.calculate_score({"q1": 0, "q2": 0}, {"q1": 0, "q2": 1}) == 50.0


def test_calculate_score_no_questions():
    assert gamification.calculate_score({}, {}) == 0.0


def test_incorrect_concepts_deduplicates():
    answers = {"q1": 1, "q2": 1, "q3": 0}
    answer_key = {"q1": 0, "q2": 0, "q3": 0}
    concept_by_question = {"q1": "fractions", "q2": "fractions", "q3": "addition"}
    result = gamification.incorrect_concepts(answers, answer_key, concept_by_question)
    assert result == ["fractions"]


def test_compute_streak_first_session():
    streak, incremented = gamification.compute_streak(0, None, datetime.now(timezone.utc))
    assert streak == 1 and incremented is True


def test_compute_streak_same_day_no_change():
    now = datetime(2026, 8, 27, 10, tzinfo=timezone.utc)
    last = datetime(2026, 8, 27, 8, tzinfo=timezone.utc)
    streak, incremented = gamification.compute_streak(3, last, now)
    assert streak == 3 and incremented is False


def test_compute_streak_next_day_increments():
    now = datetime(2026, 8, 28, 9, tzinfo=timezone.utc)
    last = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    streak, incremented = gamification.compute_streak(3, last, now)
    assert streak == 4 and incremented is True


def test_compute_streak_gap_resets():
    now = datetime(2026, 9, 5, 9, tzinfo=timezone.utc)
    last = datetime(2026, 8, 27, 9, tzinfo=timezone.utc)
    streak, incremented = gamification.compute_streak(5, last, now)
    assert streak == 1 and incremented is True


def test_compute_trend_no_history_is_stable():
    assert gamification.compute_trend([], 90) == "stable"


def test_compute_trend_improving():
    assert gamification.compute_trend([60, 65], 80) == "improving"


def test_compute_trend_declining():
    assert gamification.compute_trend([80, 85], 60) == "declining"


def test_compute_xp_completion_only():
    xp, breakdown = gamification.compute_xp(completed=True, score=50, improved=False, streak_incremented=False)
    assert xp == 10 and breakdown == {"completion": 10}


def test_compute_xp_all_bonuses():
    xp, breakdown = gamification.compute_xp(completed=True, score=90, improved=True, streak_incremented=True)
    assert xp == 30
    assert breakdown == {"completion": 10, "high_score": 10, "improvement": 5, "streak": 5}


def test_compute_xp_never_awarded_when_not_completed():
    xp, breakdown = gamification.compute_xp(completed=False, score=90, improved=True, streak_incremented=True)
    assert "completion" not in breakdown


def test_update_concept_history_appends_and_trims_to_window():
    history = {}
    for correct in [True, False, True, True, False, True]:  # 6 attempts, window is 5
        history = gamification.update_concept_history(history, {"fractions": correct})
    assert history["fractions"] == [False, True, True, False, True]  # oldest dropped


def test_update_concept_history_independent_per_concept_key():
    """No concept name is special-cased — any slug works the same way."""
    history = gamification.update_concept_history({}, {"any_arbitrary_concept_slug": True})
    assert history["any_arbitrary_concept_slug"] == [True]


def test_concept_mastery_score_empty_history_is_neutral():
    assert gamification.concept_mastery_score([]) == gamification.NEUTRAL_MASTERY


def test_concept_mastery_score_single_correct_does_not_jump_to_strong():
    # one lucky answer on a brand-new concept shouldn't alone claim mastery
    score = gamification.concept_mastery_score([True])
    assert gamification.NEUTRAL_MASTERY < score < gamification.STRONG_THRESHOLD


def test_concept_mastery_score_all_correct_is_high():
    score = gamification.concept_mastery_score([True, True, True, True, True])
    assert score >= gamification.STRONG_THRESHOLD


def test_concept_mastery_score_all_incorrect_is_low():
    score = gamification.concept_mastery_score([False, False, False, False, False])
    assert score < gamification.WEAK_THRESHOLD


def test_concept_state_bands():
    assert gamification.concept_state(10) == "weak"
    assert gamification.concept_state(65) == "improving"
    assert gamification.concept_state(90) == "strong"


# --- requirement scenarios (ACCEPTANCE_TESTS-style) -------------------------


def test_weak_concept_remains_weak_after_poor_performance():
    history = {}
    for _ in range(3):
        history = gamification.update_concept_history(history, {"fractions_comparison": False})
    mastery = gamification.compute_mastery_map(history)
    weak, strong = gamification.derive_weak_strong(mastery)
    assert "fractions_comparison" in weak
    assert "fractions_comparison" not in strong


def test_repeated_improvement_moves_concept_toward_strong():
    history = {"fractions_comparison": [False, False, False]}  # already weak
    states = []
    for _ in range(5):
        history = gamification.update_concept_history(history, {"fractions_comparison": True})
        score = gamification.concept_mastery_score(history["fractions_comparison"])
        states.append(gamification.concept_state(score))
    assert states[0] in ("weak", "improving")
    assert states[-1] == "strong"
    # progression must be monotonic toward strong, never regress while
    # evidence keeps improving
    order = {"weak": 0, "improving": 1, "strong": 2}
    assert all(order[a] <= order[b] for a, b in zip(states, states[1:]))


def test_hundred_percent_performance_improves_mastery():
    history = {"fractions_comparison": [False, False]}  # weak from repeated misses
    before = gamification.concept_mastery_score(history["fractions_comparison"])

    history = gamification.update_concept_history(history, {"fractions_comparison": True})
    after = gamification.concept_mastery_score(history["fractions_comparison"])

    assert after > before


def test_later_poor_performance_causes_regression():
    history = {"fractions_comparison": [True, True, True, True, True]}  # strong
    before_state = gamification.concept_state(
        gamification.concept_mastery_score(history["fractions_comparison"])
    )
    assert before_state == "strong"

    for _ in range(2):
        history = gamification.update_concept_history(history, {"fractions_comparison": False})
    after_state = gamification.concept_state(
        gamification.concept_mastery_score(history["fractions_comparison"])
    )

    assert after_state != "strong"


def test_derive_weak_strong():
    mastery = {"a": 30.0, "b": 60.0, "c": 90.0}
    weak, strong = gamification.derive_weak_strong(mastery)
    assert weak == ["a"]
    assert strong == ["c"]
