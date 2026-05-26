"""Tests for actor impact scoring helpers."""
from services.actor_impact_utils import canonical_actor, impact_label, prob_label_to_pct, scenario_valence, validate_claims
from models.prospective import ProspectiveScenario


def test_impact_labels():
    assert impact_label(-2.0) == "molt_negatiu"
    assert impact_label(0.0) == "neutral"
    assert impact_label(1.8) == "molt_positiu"


def test_scenario_valence_infern():
    sc = ProspectiveScenario(
        id=1,
        project_id=1,
        name="Escenari Infern",
        scenario_type="infern",
        probability="BAIXA",
    )
    assert scenario_valence(sc) == -1.0


def test_scenario_valence_cel():
    sc = ProspectiveScenario(
        id=2,
        project_id=1,
        name="Escenari Cel",
        scenario_type="cel",
        probability="BAIXA",
    )
    assert scenario_valence(sc) == 1.0


def test_canonical_actor_aliases():
    assert canonical_actor("China") == "Xina"
    assert canonical_actor("USA") == "Estats Units"


def test_validate_claims_requires_citation():
    claims = [
        {
            "claim": "Test",
            "evidence": [{"source_url": "https://example.com/a", "excerpt": "text"}],
        },
        {"claim": "Sense font", "evidence": []},
    ]
    v = validate_claims(claims)
    assert v["claims_total"] == 2
    assert v["claims_supported"] == 1
    assert v["claims_without_citation"] == 1
