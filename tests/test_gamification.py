from datetime import datetime, timezone

import pytest

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


# --- GRADE-001 ---------------------------------------------------------------


@pytest.mark.parametrize(
    "score,expected_letter",
    [
        (100, "A"),
        (80, "A"),
        (79, "B"),
        (60, "B"),
        (59, "C"),
        (40, "C"),
        (39, "D"),
        (0, "D"),
    ],
)
def test_compute_grade_boundaries(score, expected_letter):
    letter, _label = gamification.compute_grade(score)
    assert letter == expected_letter


def test_compute_grade_returns_label_too():
    assert gamification.compute_grade(100) == ("A", "Excellent")
    assert gamification.compute_grade(0) == ("D", "Needs Improvement")


def test_compute_grade_never_calls_gemini():
    # Regression guard for "Gemini must not assign a Grade" (AI_SPEC.md §5):
    # this module has no import of ai_engine/genai at all.
    import inspect

    source = inspect.getsource(gamification)
    assert "genai" not in source and "ai_engine" not in source


# --- LEVEL-001 -----------------------------------------------------------------


@pytest.mark.parametrize(
    "total_xp,expected_level,expected_name",
    [
        (0, 1, "Starter"),
        (49, 1, "Starter"),
        (50, 2, "Learner"),
        (149, 2, "Learner"),
        (150, 3, "Achiever"),
        (299, 3, "Achiever"),
        (300, 4, "Scholar"),
        (499, 4, "Scholar"),
        (500, 5, "Master"),
        (10_000, 5, "Master"),
    ],
)
def test_compute_level_boundaries(total_xp, expected_level, expected_name):
    level, name = gamification.compute_level(total_xp)
    assert (level, name) == (expected_level, expected_name)


# --- STREAK-001 ----------------------------------------------------------------


def test_strike_status_zero_streak():
    now = datetime(2026, 8, 27, 10, tzinfo=timezone.utc)
    assert gamification.strike_status(0, None, now) == "Start your streak"


def test_strike_status_positive_streak_completed_today():
    now = datetime(2026, 8, 27, 10, tzinfo=timezone.utc)
    last = datetime(2026, 8, 27, 8, tzinfo=timezone.utc)
    assert gamification.strike_status(3, last, now) == "🔥 Done today"


def test_strike_status_positive_streak_not_completed_today():
    now = datetime(2026, 8, 27, 10, tzinfo=timezone.utc)
    last = datetime(2026, 8, 26, 8, tzinfo=timezone.utc)  # yesterday
    assert gamification.strike_status(3, last, now) == "⏳ Streak alive — practice today"


def test_strike_status_date_boundary_just_after_midnight():
    # last session was 23:59 yesterday, now is 00:01 today -- still "not
    # completed today" even though less than 3 minutes have passed
    now = datetime(2026, 8, 27, 0, 1, tzinfo=timezone.utc)
    last = datetime(2026, 8, 26, 23, 59, tzinfo=timezone.utc)
    assert gamification.strike_status(2, last, now) == "⏳ Streak alive — practice today"


def test_strike_status_zero_streak_ignores_last_session_at():
    # defensive: streak==0 always wins, even if last_session_at is oddly set
    now = datetime(2026, 8, 27, 10, tzinfo=timezone.utc)
    assert gamification.strike_status(0, now, now) == "Start your streak"


# --- HIST-001: session_result_trend ---------------------------------------------


def test_session_result_trend_no_previous():
    assert gamification.session_result_trend(None, 80) == "—"


def test_session_result_trend_improved():
    assert gamification.session_result_trend(60, 80) == "Improved"


def test_session_result_trend_declined():
    assert gamification.session_result_trend(80, 60) == "Declined"


def test_session_result_trend_same():
    assert gamification.session_result_trend(70, 70) == "Same"


# --- HIST-001: reconstruct_session_xp_history -----------------------------------


def test_reconstruct_session_xp_history_matches_live_computation():
    """The replayed XP must exactly match what compute_xp would have
    produced live, for a simple two-session sequence."""
    d1 = datetime(2026, 8, 25, 9, tzinfo=timezone.utc)
    d2 = datetime(2026, 8, 26, 9, tzinfo=timezone.utc)  # consecutive day -> streak increments

    xp_series = gamification.reconstruct_session_xp_history([(50.0, d1), (90.0, d2)])

    # session 1: first ever -> streak_incremented=True, no recent_scores -> trend "stable" -> improved=False
    expected_xp1, _ = gamification.compute_xp(
        completed=True, score=50.0, improved=False, streak_incremented=True
    )
    # session 2: consecutive day -> streak_incremented=True; trend vs [50.0] -> "improving" -> improved=True
    trend2 = gamification.compute_trend([50.0], 90.0)
    expected_xp2, _ = gamification.compute_xp(
        completed=True, score=90.0, improved=(trend2 == "improving"), streak_incremented=True
    )

    assert xp_series == [expected_xp1, expected_xp2]


def test_reconstruct_session_xp_history_empty():
    assert gamification.reconstruct_session_xp_history([]) == []
