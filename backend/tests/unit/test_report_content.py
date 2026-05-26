"""Unit tests for report executive summary and variable profiles."""
from types import SimpleNamespace

import pytest

from services.report_content import build_executive_summary, build_variable_profiles
from services.report_i18n import get_report_strings, normalize_lang


@pytest.mark.unit
def test_normalize_lang_defaults_to_ca():
    assert normalize_lang(None) == "ca"
    assert normalize_lang("es") == "es"
    assert normalize_lang("fr") == "ca"


@pytest.mark.unit
def test_build_variable_profiles_includes_motivation():
    bundle = {
        "lang": "ca",
        "variables": [
            SimpleNamespace(code="V1", name="Tensions comercials", var_type="I", description="Pressió aranzelària"),
        ],
        "micmac": SimpleNamespace(
            sectors=[{"code": "V1", "sector": "Clau/Conflicte", "motricite": 0.8, "dependencia": 0.3}],
            motricite_direct=[0.8],
            dependence_direct=[0.3],
        ),
        "suggested_variables": [
            {"code": "V1", "name": "Tensions comercials", "rationale": "Apareix en 12 declaracions hostils"},
        ],
        "micmac_suggestions": None,
        "retrospective": {"micmac_evidence": {"pairs": []}},
        "statements": [],
    }
    profiles = build_variable_profiles(bundle)
    assert len(profiles) == 1
    assert profiles[0]["code"] == "V1"
    assert "Pressió aranzelària" in profiles[0]["motivation"]
    assert "12 declaracions" in profiles[0]["osint_rationale"]


@pytest.mark.unit
def test_build_executive_summary_sections_es():
    bundle = {
        "lang": "es",
        "project": SimpleNamespace(hypothesis="H1", context="C1", title="T", id=1),
        "variables": [],
        "scenarios": [SimpleNamespace(name="Escenario A", scenario_type="tension", probability="35%")],
        "osint_articles": [{}],
        "statements": [],
        "retrospective": None,
        "actor_impact": {"has_data": False},
        "investment": {"has_data": False, "risks": [], "opportunities": []},
    }
    bundle["variable_profiles"] = build_variable_profiles(bundle)
    summary = build_executive_summary(bundle)
    s = get_report_strings("es")
    assert summary["sections"][0]["title"] == s.es_objective
    assert any("H1" in p for p in summary["sections"][0]["paragraphs"])
