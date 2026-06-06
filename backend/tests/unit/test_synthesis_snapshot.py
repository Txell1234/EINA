"""Snapshot-style regression tests for deterministic inquiry synthesis."""
import pytest

from services.prospective_synthesis_service import ProspectiveSynthesisService


FIXTURE = {
    "question": "Trump announces US blockade of Hormuz lifted by December 2026?",
    "parsed_trigger": {
        "actors": ["US", "Iran"],
        "required_terms": ["hormuz", "blockade"],
        "horizon_label": "12m",
    },
    "actor_impact": {"osint_signals": {"hostile_statements": 3, "cooperative_statements": 1}},
    "scenarios": [{"name": "Tensió", "estimated_probability_pct": 38, "possibility": "PLAUSIBLE"}],
    "financial_crossover": {"mode": "lite", "crossover": {"final_numbers": {"blended_return_index": 62}}},
    "policy_industry": {"companies": [{"name": "Acme Energy"}]},
    "morph_bootstrap": {"valid_combinations_count": 15, "godet_preview": [{"name": "Equilibri", "possibility": "PLAUSIBLE"}]},
    "monitor_suggestions": {"suggested_monitors": [{"indicator": "Test monitor"}]},
    "godet_ready": True,
}


@pytest.mark.unit
def test_synthesis_snapshot_keys():
    answer = ProspectiveSynthesisService().synthesize(**FIXTURE)
    assert answer["llm_used_in_conclusions"] is False
    assert answer["methodology"] == "deterministic_synthesis"
    assert answer["probability_pct"] == 38.0
    assert answer["financial_mode"] == "lite"
    assert answer["policy_companies_count"] == 1
    assert answer["suggested_monitors_count"] == 1
    assert len(answer["reasoning"]) >= 3
    assert answer["confidence"] >= 40


@pytest.mark.unit
def test_synthesis_snapshot_stable_conclusions():
    a1 = ProspectiveSynthesisService().synthesize(**FIXTURE)
    a2 = ProspectiveSynthesisService().synthesize(**FIXTURE)
    assert a1["conclusions"] == a2["conclusions"]
    assert a1["probability_pct"] == a2["probability_pct"]
