"""Tests for extract validation grounding and verifiability."""
import pytest
from types import SimpleNamespace

from services.extract_validation import (
    effective_grounding_score,
    is_verifiable_source,
    validate_statements,
)


@pytest.mark.unit
def test_effective_grounding_never_self_compares():
    stmt = "El Japó veu la Xina com un desafiament estratègic per la seva pressió militar."
    assert effective_grounding_score(stmt, "") is None
    assert effective_grounding_score(stmt, None) is None


@pytest.mark.unit
def test_fake_100pct_from_self_compare_removed():
    s = SimpleNamespace(
        id=1,
        statement="El Japó veu la Xina com un desafiament estratègic.",
        context="",
        topic="",
        source_url="",
        source_text_excerpt="",
        grounding_score=1.0,
        actor="Govern del Japó",
        tone="neutral",
        relevance_signals=[],
        cleanup_decision="KEEP",
    )
    result = validate_statements([s])
    assert result["unverified_count"] == 1
    assert result["avg_grounding"] == 0.0


@pytest.mark.unit
def test_is_verifiable_source_requires_url_and_excerpt():
    assert is_verifiable_source("https://ecfr.eu/article", "How China's silent coercion has Europe sanctioning itself") is True
    assert is_verifiable_source("", "some excerpt long enough to pass the minimum length check here") is False
    assert is_verifiable_source("direct-analysis:synthetic", "x" * 50) is False
