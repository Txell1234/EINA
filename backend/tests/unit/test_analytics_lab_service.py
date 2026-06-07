"""Tests for Analytics Lab (Phase C)."""
import pytest

from services.analytics_lab_service import (
    AnalyticsLabService,
    run_monte_carlo_icg,
    run_shap_like_attribution,
    run_sobol_first_order,
    run_tornado_sensitivity,
)

_COMPONENTS = [
    {"name": "osint_traceability", "label": "Traçabilitat", "value": 78.0, "weight": 0.25},
    {"name": "geopolitical_risk_environment", "label": "Risc geo", "value": 35.0, "weight": 0.30},
    {"name": "scenario_outlook", "label": "Escenaris", "value": 62.0, "weight": 0.20},
    {"name": "eina_gma", "label": "GMA", "value": 74.0, "weight": 0.10},
]


@pytest.mark.unit
def test_tornado_sensitivity_swing():
    rows = run_tornado_sensitivity(_COMPONENTS, base_icg=58.0, perturb_pct=20.0)
    assert len(rows) == 4
    assert all(r.get("swing") is not None for r in rows)
    assert rows[0]["swing"] >= rows[-1]["swing"]


@pytest.mark.unit
def test_monte_carlo_distribution():
    out = run_monte_carlo_icg(_COMPONENTS, n_samples=200, seed=1)
    assert out["n"] == 200
    assert out["mean"] is not None
    assert out["p5"] <= out["p95"]


@pytest.mark.unit
def test_shap_attribution_sums_to_icg():
    attrs = run_shap_like_attribution(_COMPONENTS)
    base = sum(a["contribution"] for a in attrs)
    assert abs(base - 58.0) < 2.0


@pytest.mark.unit
def test_sobol_first_order():
    indices = run_sobol_first_order(_COMPONENTS, n_samples=128, seed=3)
    assert len(indices) >= 1
    assert all(0 <= i["sobol_first_order"] <= 1 for i in indices)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analytics_lab_run_and_cache():
    lab = AnalyticsLabService()
    bundle = {
        "geopolitical_confidence_index": 58.0,
        "geopolitical_confidence_components": _COMPONENTS,
        "eina_gma": 74.0,
        "sanction_impact_score": 72.0,
        "sanction_entity_impacts": [{"entity": "Iran", "score": 80}],
    }
    r1 = await lab.run(99, confidence_bundle=bundle, experiments=["tornado", "monte_carlo"])
    assert "tornado" in r1
    assert "monte_carlo" in r1
    r2 = await lab.run(99, confidence_bundle=bundle, experiments=["tornado", "monte_carlo"])
    assert r2.get("cached") is True
    latest = lab.get_latest(99)
    assert latest is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analytics_lab_entity_scope():
    from services.analytics_lab_service import resolve_lab_confidence

    entity_components = [
        {"name": "case_baseline", "label": "Baseline", "value": 58.0, "weight": 0.35},
        {"name": "entity_policy_exposure", "label": "Policy", "value": 42.0, "weight": 0.20},
    ]
    bundle = {
        "geopolitical_confidence_index": 58.0,
        "geopolitical_confidence_components": _COMPONENTS,
        "entity_confidence_index": 45.0,
        "entity_confidence_components": entity_components,
        "focus_company": "Maersk",
        "entity_icg_delta": -13.0,
    }
    comps, base, scope = resolve_lab_confidence(bundle, scope="entity")
    assert scope == "entity"
    assert base == 45.0
    assert len(comps) == 2

    lab = AnalyticsLabService()
    result = await lab.run(101, confidence_bundle=bundle, experiments=["tornado"], confidence_scope="entity")
    assert result["confidence_scope"] == "entity"
    assert result["base_icg"] == 45.0
    assert result["case_icg_baseline"] == 58.0
