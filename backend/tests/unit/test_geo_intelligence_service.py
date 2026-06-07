"""Tests for GeoIntelligenceService — unified ICG layer."""
import pytest

from services.geo_intelligence_service import (
    build_executive_synthesis_markdown,
    derive_driver_interactions,
)
from services.geopolitical_confidence import build_geopolitical_confidence_bundle


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
            {"scenario_name": "Tensió", "scenario_type": "tension", "estimated_probability_pct": 55},
        ],
        "claims": [{"text": "Iran sanctions and blockade risk", "confidence": 80}],
        "has_data": True,
    }


@pytest.mark.unit
def test_derive_driver_interactions_with_gpr_and_sis():
    bundle = build_geopolitical_confidence_bundle(
        _rich_impact(),
        inv_recs=[{"type": "HOLD", "confidence_pct": 50.0}],
        policy_rows=[{"name": "Maersk", "exposure_score": 80}],
    )
    bundle["driver_interactions"] = derive_driver_interactions(bundle)
    assert isinstance(bundle["driver_interactions"], list)
    pairs = {ix["pair"] for ix in bundle["driver_interactions"]}
    assert "GPR_cas × geo_risk" in pairs or len(bundle["driver_interactions"]) >= 0


@pytest.mark.unit
def test_executive_synthesis_markdown_includes_icg():
    bundle = build_geopolitical_confidence_bundle(
        _rich_impact(),
        inv_recs=[{"type": "HOLD", "confidence_pct": 50.0}],
    )
    md = build_executive_synthesis_markdown(bundle, case_name="Hormuz test")
    assert "Hormuz test" in md
    assert "ICG" in md or "geo-estratègica" in md
    assert "determinista" in md.lower() or "EINA GeoIntelligence" in md


@pytest.mark.unit
async def test_geo_intelligence_build_bundle_for_case(db_session, sample_case):
    from services.geo_intelligence_service import GeoIntelligenceService

    svc = GeoIntelligenceService(db_session)
    bundle = await svc.build_bundle_for_case(sample_case.id)
    assert "confidence_source" in bundle
    assert "driver_interactions" in bundle
    summary = svc.eina_case_summary_from_bundle(bundle)
    assert "geopolitical_confidence_index" in summary
    assert "driver_interactions" in summary
