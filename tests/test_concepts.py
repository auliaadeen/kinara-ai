from src.utils.concepts import normalize_concept


def test_normalize_lowercases_and_underscores():
    assert normalize_concept("Comparing Fractions") == "comparing_fractions"


def test_normalize_handles_alternate_phrasing_same_result():
    assert normalize_concept("fraction comparison!!") == normalize_concept("Fraction Comparison")


def test_normalize_empty_falls_back_to_general():
    assert normalize_concept("   ") == "general"
