"""Tests for extract validation (china-us-rhetoric pattern)."""
from services.extract_validation import (
    grounding_score,
    has_domestic_signal,
    has_international_signal,
    tokenize_for_grounding,
)


def test_grounding_score_with_stopwords():
    quote = "Japan will increase defense spending significantly"
    article = "Tokyo announced Japan will increase defense spending in the next fiscal year"
    score = grounding_score(quote, article)
    assert score >= 0.5


def test_international_signal_japan():
    assert has_international_signal("Japan rearmament concerns NATO allies", "", "")


def test_international_signal_coded_language():
    assert has_international_signal("Les potències occidentals pressionen el govern", "", "")


def test_domestic_signal():
    assert has_domestic_signal("Reforma del sistema de pensions nacional", "", "")


def test_tokenize_filters_short_words():
    words = tokenize_for_grounding("the cat sat on mat")
    assert "the" not in words
    assert "cat" not in words  # len < 4
    assert "sat" not in words
