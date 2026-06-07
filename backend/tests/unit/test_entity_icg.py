"""Tests for ICE_entitat vs ICG_cas dual confidence model."""
import pytest

from services.geopolitical_confidence import (
    build_case_icg_bundle,
    build_entity_icg_bundle,
    build_geopolitical_confidence_bundle,
)


def _hormuz_impact() -> dict:
    return {
        "summary": {"overall_confidence": 78.0, "claim_count": 12, "export_ready": True},
        "validation": {"export_ready": True},
        "osint_signals": {
            "avg_geopolitical_risk": 72.0,
            "hostility_ratio": 0.35,
            "conflict_events": 2,
        },
        "scenario_justifications": [
            {
                "scenario_name": "Equilibri regional",
                "scenario_type": "equilibri",
                "estimated_probability_pct": 42,
            },
            {
                "scenario_name": "Tensió crònica",
                "scenario_type": "tension",
                "estimated_probability_pct": 38,
            },
            {
                "scenario_name": "Conflicte Hormuz",
                "scenario_type": "conflict",
                "estimated_probability_pct": 20,
            },
        ],
        "claims": [
            {
                "claim": "Maersk reroutes via Cape due to Hormuz blockade",
                "confidence": 68,
                "actors": ["Maersk"],
            },
            {
                "claim": "Kawasaki export controls on defense components",
                "confidence": 71,
                "actors": ["Kawasaki"],
            },
        ],
        "actors": [
            {"name": "Maersk Line", "geo_risk_score": 62},
            {"name": "Kawasaki Heavy Industries", "geo_risk_score": 55},
        ],
        "has_data": True,
    }


@pytest.mark.unit
def test_icg_cas_stable_without_focus():
    impact = _hormuz_impact()
    case = build_case_icg_bundle(impact, policy_rows=[{"name": "Maersk", "sectors": ["shipping"]}])
    bundle_no_focus = build_geopolitical_confidence_bundle(impact, policy_rows=[{"name": "Maersk", "sectors": ["shipping"]}])
    assert case["index"] is not None
    assert bundle_no_focus["geopolitical_confidence_index"] == case["index"]
    assert bundle_no_focus["entity_icg"] is None
    names = {c["name"] for c in case["components"]}
    assert "focus_entity_exposure" not in names
    assert "osint_traceability" in names


@pytest.mark.unit
def test_ice_differs_for_shipping_vs_defense():
    impact = _hormuz_impact()
    case = build_case_icg_bundle(impact, policy_rows=[])

    maersk_ice = build_entity_icg_bundle(
        impact,
        focus_company="Maersk",
        case_icg=case,
        entity_focus_match={"name": "Maersk"},
        registry_row={"name": "Maersk", "sectors": ["shipping"], "region": "overseas"},
        external_metrics={
            "investwatch_summary": {"avg_return_score": 3.0, "avg_risk_score": 6.0},
            "recommendation": "HOLD",
        },
        sanction_entity_impacts=[{"entity": "Maersk", "score": 55, "because": "blockade"}],
    )
    kawasaki_ice = build_entity_icg_bundle(
        impact,
        focus_company="Kawasaki",
        case_icg=case,
        entity_focus_match={"name": "Kawasaki Heavy Industries"},
        registry_row={"name": "Kawasaki Heavy Industries", "sectors": ["defense"], "region": "overseas"},
        sanction_entity_impacts=[{"entity": "Kawasaki", "score": 30, "because": "export"}],
    )

    assert maersk_ice is not None
    assert kawasaki_ice is not None
    assert maersk_ice["index"] != kawasaki_ice["index"]
    assert maersk_ice["index"] < kawasaki_ice["index"]
    assert maersk_ice["delta_vs_case"] != kawasaki_ice["delta_vs_case"]
    assert maersk_ice["delta_vs_case"] < kawasaki_ice["delta_vs_case"]


@pytest.mark.unit
def test_hormuz_ice_calibration_ranges():
    """Hormuz-style spread: shipping well below case, defense closer to case."""
    impact = _hormuz_impact()
    case = build_case_icg_bundle(impact, policy_rows=[])
    case_icg = float(case["index"])

    maersk = build_entity_icg_bundle(
        impact,
        focus_company="Maersk",
        case_icg=case,
        entity_focus_match={"name": "Maersk"},
        registry_row={"name": "Maersk", "sectors": ["shipping"], "region": "overseas"},
        external_metrics={
            "investwatch_summary": {"avg_return_score": 3.0, "avg_risk_score": 6.0},
            "recommendation": "HOLD",
        },
        sanction_entity_impacts=[{"entity": "Maersk", "score": 55, "because": "blockade"}],
    )
    kawasaki = build_entity_icg_bundle(
        impact,
        focus_company="Kawasaki",
        case_icg=case,
        entity_focus_match={"name": "Kawasaki Heavy Industries"},
        registry_row={"name": "Kawasaki Heavy Industries", "sectors": ["defense"], "region": "overseas"},
        sanction_entity_impacts=[{"entity": "Kawasaki", "score": 30, "because": "export"}],
    )

    assert maersk is not None and kawasaki is not None
    assert 38.0 <= maersk["index"] <= 46.0
    assert 52.0 <= kawasaki["index"] <= 59.0
    assert maersk["index"] - case_icg <= -5.0
    assert kawasaki["index"] - maersk["index"] >= 10.0


@pytest.mark.unit
def test_bundle_dual_with_focus_company():
    impact = _hormuz_impact()
    bundle = build_geopolitical_confidence_bundle(
        impact,
        focus_company="Maersk",
        entity_focus_match={"name": "Maersk"},
        registry_row={"name": "Maersk", "sectors": ["shipping"], "region": "overseas"},
        external_metrics={"investwatch_summary": {"avg_risk_score": 6.5, "avg_return_score": 2.5}},
    )
    assert bundle["case_icg"]["index"] is not None
    assert bundle["entity_icg"] is not None
    assert bundle["entity_confidence_index"] == bundle["entity_icg"]["index"]
    assert bundle["geopolitical_confidence_index"] == bundle["case_icg"]["index"]
    assert bundle["entity_icg_delta"] is not None
    assert len(bundle["entity_confidence_components"]) >= 4
