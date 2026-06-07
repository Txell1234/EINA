"""Unit tests for Geopolitical Confidence Index (ICG)."""
import pytest

from services.geopolitical_confidence import (
    apply_gpr_dynamic_weights,
    build_case_icg_bundle,
    build_geopolitical_confidence_bundle,
    gpr_multiplier_sigmoid,
)


def _rich_impact() -> dict:
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
        ],
        "claims": [
            {"claim": "Kawasaki exposada a exportacions", "confidence": 71, "actors": ["Kawasaki"]},
        ],
        "actors": [{"name": "Kawasaki Heavy Industries", "geo_risk_score": 55}],
        "has_data": True,
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "avg_gpr, expected_min, expected_max",
    [
        (20.0, 0.86, 0.87),
        (68.0, 1.32, 1.33),
        (100.0, 1.74, 1.75),
    ],
)
def test_gpr_multiplier_sigmoid(avg_gpr, expected_min, expected_max):
    m = gpr_multiplier_sigmoid(avg_gpr)
    assert expected_min <= m <= expected_max


@pytest.mark.unit
def test_icg_computed_with_components():
    bundle = build_geopolitical_confidence_bundle(
        _rich_impact(),
        inv_recs=[{"type": "HOLD", "confidence_pct": 50.0, "rationale": "default"}],
        focus_company="Kawasaki",
        entity_focus_match={"name": "Kawasaki Heavy Industries"},
        registry_row={"name": "Kawasaki Heavy Industries", "sectors": ["defense"]},
    )
    assert bundle["geopolitical_confidence_index"] is not None
    assert bundle["case_icg"]["index"] is not None
    assert bundle["entity_icg"] is not None
    assert bundle["entity_confidence_index"] is not None
    assert bundle["confidence_source"] in ("computed", "partial")
    assert len(bundle["components"]) >= 3
    assert bundle["investment_posture"]["source"] == "default_fallback"
    assert bundle["geopolitical_confidence_index"] != 50.0
    names = {c["name"] for c in bundle["components"]}
    assert "eina_gma" in names
    assert "focus_entity_exposure" not in names


@pytest.mark.unit
def test_icg_missing_without_data():
    bundle = build_geopolitical_confidence_bundle(
        {},
        inv_recs=[{"type": "HOLD", "confidence_pct": 50.0}],
    )
    assert bundle["geopolitical_confidence_index"] is None
    assert bundle["confidence_source"] == "missing"
    assert bundle["components"] == []


@pytest.mark.unit
def test_gpr_dynamic_weights_normalize():
    components = [
        {"name": "osint_traceability", "value": 80, "base_weight": 0.25},
        {"name": "geopolitical_risk_environment", "value": 30, "base_weight": 0.25},
    ]
    weighted = apply_gpr_dynamic_weights(components, 90.0)
    assert abs(sum(c["weight"] for c in weighted) - 1.0) < 0.0001
    risk = next(c for c in weighted if c["name"] == "geopolitical_risk_environment")
    assert risk["weight"] > 0.25


@pytest.mark.unit
def test_eina_gma_component():
    from services.geopolitical_confidence import compute_eina_gma

    gma = compute_eina_gma(_rich_impact(), policy_rows=[{"name": "Kawasaki", "sectors": ["defense"]}])
    assert gma["value"] is not None
    assert 0 <= gma["value"] <= 100
    assert "formula_detail" in gma


@pytest.mark.unit
def test_sis_high_with_sanction_claims():
    from services.geopolitical_confidence import compute_sanction_impact

    impact = _rich_impact()
    impact["claims"] = [
        {"claim": "OFAC expanded sanctions on Iranian shipping", "confidence": 80, "actors": ["Iran"]},
        {"claim": "Embargo on dual-use exports", "confidence": 70},
    ]
    sis = compute_sanction_impact(
        impact,
        scenarios=[{"name": "Equilibri", "type": "equilibri"}, {"name": "Conflicte", "type": "conflict"}],
        focus_company="Kawasaki",
        policy_rows=[{"name": "Kawasaki Heavy Industries", "sectors": ["defense"]}],
    )
    assert sis["sanction_impact_score"] is not None
    assert sis["sanction_impact_score"] >= 50
    assert len(sis["drivers"]) >= 1
    assert sis["scenario_probability_adjustments"]


@pytest.mark.unit
def test_build_case_icg_excludes_entity_focus():
    case = build_case_icg_bundle(_rich_impact(), policy_rows=[{"name": "Kawasaki", "sectors": ["defense"]}])
    assert case["index"] is not None
    assert all(c["name"] != "focus_entity_exposure" for c in case["components"])
