"""Tests for inquiry scope must-match filtering."""
import pytest

from services.inquiry_scope import (
    build_inquiry_scope,
    is_article_in_inquiry_scope,
    score_inquiry_relevance,
)


HORMUZ_Q = (
    "Trump announces US blockade of Hormuz lifted by December 2026?"
)
JAPAN_Q = "Japanese rearmament and JSDF defense budget increase by 2030?"


@pytest.mark.unit
def test_build_inquiry_scope_hormuz():
    scope = build_inquiry_scope(HORMUZ_Q)
    assert len(scope.required_terms) >= 2
    assert scope.min_required_matches >= 1
    assert any("trump" in t for t in scope.required_terms)
    assert scope.min_relevance >= 0.4


@pytest.mark.unit
def test_hormuz_article_passes():
    scope = build_inquiry_scope(HORMUZ_Q)
    text = (
        "Trump administration signals possible easing of Hormuz naval blockade "
        "after talks with Gulf mediators in December 2026."
    )
    diag = score_inquiry_relevance(text, "Trump Hormuz blockade", inquiry=scope)
    assert diag["passed_must_match"] is True
    assert diag["passed"] is True


@pytest.mark.unit
def test_japan_article_rejected_for_hormuz_scope():
    scope = build_inquiry_scope(HORMUZ_Q)
    text = (
        "Japan approves record JSDF defense budget focusing on Indo-Pacific "
        "rearmament and missile defense systems."
    )
    diag = score_inquiry_relevance(text, "Japan defense budget", inquiry=scope)
    assert diag["passed"] is False


@pytest.mark.unit
def test_japan_scope_accepts_japan_article():
    scope = build_inquiry_scope(JAPAN_Q)
    text = "Japan JSDF rearmament budget increase approved for defense modernization."
    assert is_article_in_inquiry_scope(text, "Japan defense", inquiry=scope) is True
