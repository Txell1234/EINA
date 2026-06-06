"""Tests for morph bootstrap service."""
import pytest

from services.morph_bootstrap_service import MorphBootstrapService


@pytest.mark.unit
def test_morph_bootstrap_security_maritime():
    svc = MorphBootstrapService()
    result = svc.bootstrap(
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        event_type="security_maritime",
        actors=["US", "Iran"],
    )
    assert result["llm_used"] is False
    assert len(result["suggested_components"]) >= 3
    assert result["valid_combinations_count"] >= 1
    assert len(result["godet_preview"]) <= 4
    assert result["methodology"] == "rule_based_morph_bootstrap"


@pytest.mark.unit
def test_morph_bootstrap_default_geopolitical():
    result = MorphBootstrapService().bootstrap(question="Bilateral relations normalize by 2027?")
    assert result["event_type"] == "geopolitical"
    assert result["valid_combinations_count"] >= 1
