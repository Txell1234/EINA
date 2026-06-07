"""Tests for EIU-style Godet outlook report sections."""
import pytest

from services.report_outlook import build_outlook_sections, parse_macro_outlook_text
from services.report_templates import normalize_report_variant


class _FakeProject:
    hypothesis = "Trade fragmentation and domestic resilience in Asia-Pacific"
    title = "Asia policy case"
    context = "US tariffs and RCEP dynamics shape the 2026 outlook."


class _FakeScenario:
    name = "RCEP gets serious"
    scenario_type = "trade"
    possibility = "PLAUSIBLE"
    probability = "70%"
    narrative = "Signatories improve implementation of technical barriers."


@pytest.mark.unit
def test_build_outlook_sections_from_bundle():
    bundle = {
        "lang": "ca",
        "project": _FakeProject(),
        "variable_profiles": [
            {
                "code": "V1",
                "name": "US trade policy",
                "motricity": 0.82,
                "dependence": 0.4,
                "motivation": "Driver of export shock in 2026.",
                "sector": "exogenous",
            }
        ],
        "scenarios": [_FakeScenario()],
        "actor_impact": {
            "has_data": True,
            "summary": {"most_likely_scenario": "RCEP gets serious", "overall_confidence": 62},
            "claims": [{"claim": "Domestic demand provides a partial backstop.", "confidence": 60}],
        },
        "investment": {
            "risks": [{"risk_type": "Political", "risk_level": "medium", "description": "Instability uptick."}],
            "opportunities": [{"title": "Services liberalisation", "description": "ASEAN integration window."}],
        },
        "executive_summary": {"sections": []},
    }
    out = build_outlook_sections(bundle)
    assert out["theme_subtitle"]
    assert len(out["what_to_watch"]) >= 2
    assert len(out["key_risks"]) >= 1
    assert len(out["key_opportunities"]) >= 1
    assert out["scenarios"][0]["likelihood_pct"] == 70


@pytest.mark.unit
def test_normalize_report_variant():
    assert normalize_report_variant("full") == "full"
    assert normalize_report_variant("analytical") == "analytical"
    assert normalize_report_variant("outlook") == "analytical"


@pytest.mark.unit
def test_parse_macro_outlook_minimal():
    text = """
Asia outlook 2026
Trade fragmentation
What to watch in 2026
Political instability will matter in 2026 although medium-term outlook stays constructive.
Key risks
Election surprises and corruption resentment continue across the region.
Key opportunities
Private consumption backstop as inflation stays contained.
RCEP gets serious (likelihood: 70%): members harmonise standards.
"""
    out = parse_macro_outlook_text(text)
    assert out is not None
    assert len(out["what_to_watch"]) >= 1
    assert out["scenarios"][0]["likelihood_pct"] == 70
