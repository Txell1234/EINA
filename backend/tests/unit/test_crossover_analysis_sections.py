"""Tests for crossover analysis enrichment sections."""
import pytest

from services.crossover_analysis_sections import (
    build_geopolitical_financial_synthesis,
    build_industry_implications,
)
from services.crossover_recommendation_service import build_tiered_recommendations

KAWASAKI_PROFILE = {
    "name": "Kawasaki Heavy Industries",
    "ticker": "7012.T",
    "country": "JP",
    "roles": ["prime_contractor"],
    "sectors": ["submarines", "aircraft", "transport"],
    "policy_link": "Expansió capacitat submarina Indo-Pacífic",
    "beneficiary_rationale": "Constructor submarins Sōryū/Taigei.",
    "contractor_relationships": [
        {"partner": "Mitsubishi Heavy Industries", "type": "naval_peer", "region": "domestic"},
    ],
    "registry_found": True,
}


@pytest.mark.unit
def test_industry_implications_include_finance_and_geo():
    metrics = {
        "primary_recommendation": "BUY",
        "upside_consensus_pct": 31.0,
        "investwatch_summary": {"avg_return_score": 4.0, "avg_risk_score": 4.69, "signal": "more_risk_than_return"},
        "key_metrics": [
            {"label": "ROA", "value_pct": 4.0},
            {"label": "ROCE", "value_pct": 13.8},
            {"label": "Revenue", "value_pct": 1.0},
        ],
    }
    eina = {
        "scenarios": [
            {"name": "Escenari Infern", "type": "infern", "probability": 25},
            {"name": "Escenari Tensió Crònica", "type": "tension", "probability": 40},
        ],
        "investment_recommendations": [{"type": "HOLD", "confidence_pct": 50, "rationale": "Incertesa geo."}],
    }
    out = build_industry_implications(
        KAWASAKI_PROFILE, metrics, eina, signal="BUY", final_numbers={"blended_return_index": 54.62}
    )
    assert len(out) == 3
    sub = next(i for i in out if i["sector"] == "submarines")
    assert "BUY" in sub["financial_read"]
    assert "Indo-Pacífic" in sub["geopolitical_read"] or "submarina" in sub["geopolitical_read"].lower()
    assert sub["peers"]


@pytest.mark.unit
def test_geopolitical_financial_synthesis_divergence():
    metrics = {
        "primary_recommendation": "BUY",
        "upside_consensus_pct": 31.0,
        "investwatch_summary": {"avg_return_score": 4.0, "avg_risk_score": 4.69, "signal": "more_risk_than_return"},
    }
    eina = {
        "scenarios": [{"name": "Tensió", "type": "tension", "probability": 40}],
        "investment_recommendations": [{"type": "HOLD", "confidence_pct": 50}],
    }
    syn = build_geopolitical_financial_synthesis(
        KAWASAKI_PROFILE,
        metrics,
        eina,
        final_numbers={"blended_return_index": 54.62, "blended_risk_index": 61.05},
        divergences=[{"summary": "Recomanació divergent: BUY vs HOLD."}],
    )
    assert len(syn["paragraphs"]) >= 2
    text = " ".join(syn["paragraphs"])
    assert "BUY" in text and "HOLD" in text


@pytest.mark.unit
def test_geopolitical_financial_synthesis_includes_sis():
    metrics = {
        "primary_recommendation": "BUY",
        "investwatch_summary": {"avg_return_score": 4.0, "avg_risk_score": 4.69},
    }
    eina = {
        "scenarios": [{"name": "Tensió", "type": "tension", "probability": 40}],
        "investment_recommendations": [{"type": "HOLD", "confidence_pct": 50}],
        "computed_confidence": {
            "geopolitical_confidence_index": 68.0,
            "sanction_impact_score": 85.0,
            "sanction_scenario_adjustments": {"Equilibri": -20, "Conflicte": +15},
            "sanction_entity_impacts": [{"entity": "Iran", "score": 90}],
            "eina_gma": 74.0,
        },
    }
    syn = build_geopolitical_financial_synthesis(KAWASAKI_PROFILE, metrics, eina)
    text = " ".join(syn["paragraphs"])
    assert "SIS" in text or "Sancions" in text
    assert "GMA" in text or "74" in text


@pytest.mark.unit
def test_geopolitical_financial_synthesis_includes_icg_breakdown():
    metrics = {
        "primary_recommendation": "BUY",
        "upside_consensus_pct": 31.0,
        "investwatch_summary": {"avg_return_score": 4.0, "avg_risk_score": 4.69, "signal": "more_risk_than_return"},
    }
    eina = {
        "scenarios": [{"name": "Tensió", "type": "tension", "probability": 40}],
        "investment_recommendations": [{"type": "HOLD", "confidence_pct": 50}],
        "computed_confidence": {
            "geopolitical_confidence_index": 68.0,
            "geopolitical_confidence_components": [
                {"label": "Traçabilitat OSINT", "value": 75.0},
                {"label": "Entorn de risc geo", "value": 55.0},
            ],
        },
    }
    syn = build_geopolitical_financial_synthesis(
        KAWASAKI_PROFILE,
        metrics,
        eina,
        final_numbers={"blended_return_index": 54.62, "blended_risk_index": 61.05},
    )
    text = " ".join(syn["paragraphs"])
    assert "ICG" in text or "geo-estratègica" in text
    assert "68" in text
    assert "Traçabilitat OSINT" in text


@pytest.mark.unit
def test_tiered_includes_analysis_sections():
    metrics = {
        "primary_recommendation": "BUY",
        "company_name": "Kawasaki Heavy Industries",
        "upside_consensus_pct": 31.0,
        "investwatch_summary": {"avg_return_score": 4.0, "avg_risk_score": 4.69},
    }
    ctx = {"reference_entity": "Kawasaki Heavy Industries", "eina_link": {"found": True, **KAWASAKI_PROFILE}}
    out = build_tiered_recommendations(
        metrics,
        {"scenarios": [{"name": "Tensió", "type": "tension"}], "investment_recommendations": [{"type": "HOLD", "confidence_pct": 50}]},
        entity_name="Kawasaki Heavy Industries",
        report_context=ctx,
        final_numbers={"blended_return_index": 54.62},
    )
    assert out.get("industry_implications")
    assert out.get("geopolitical_financial_synthesis")
    assert len(out["satellites"]) >= 2
