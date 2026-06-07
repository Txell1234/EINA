"""Tests for actor motivation and scenario enrichment."""
from services.actor_impact_utils import ensure_four_scenarios, merge_scenario_with_justification
from services.actor_motivation_service import build_actor_motivation
from models.prospective import ProspectiveScenario


def test_ensure_four_scenarios_fills_missing():
    existing = [
        ProspectiveScenario(
            id=1,
            project_id=1,
            name="Escenari Tensió Crònica",
            scenario_type="tensio",
            probability="ALTA",
        )
    ]
    out = ensure_four_scenarios(existing)
    types = {s.scenario_type for s in out}
    assert types == {"infern", "tensio", "equilibri", "cel"}
    assert len(out) == 4


def test_build_actor_motivation_uses_monitor_indicator_field():
    class Monitor:
        indicator = "Augment tensions al estret"

    class Match:
        id = 99
        monitor_id = 7
        scenario_id = None
        extracted_statement_id = None
        title = "Xina desplega vaixells"
        excerpt = "Activitat naval al estret"
        analysis_summary = ""
        matched_keywords = ["naval"]
        source_type = "gdelt"
        url = "https://example.com/naval"

    mot = build_actor_motivation(
        "Xina",
        statements=[],
        alert_matches=[Match()],
        monitors={7: Monitor()},
        scenarios_by_id={},
    )
    assert "Augment tensions" in mot["text"]


def test_build_actor_motivation_from_extraction():
    class Stmt:
        actor = "Xina"
        actor_type = "state"
        topic = "Taiwan"
        posture_value = -1
        context = "Exercicis militars prop de Taiwan"
        statement = "La Xina amenaça la sobirania"
        id = 1

    mot = build_actor_motivation("Xina", statements=[Stmt()], alert_matches=[], monitors={}, scenarios_by_id={})
    assert "Taiwan" in mot["text"] or "extracció" in mot["text"].lower()
    assert "extraction" in mot["sources"]


def test_merge_scenario_with_justification():
    sc = ProspectiveScenario(
        id=2,
        project_id=1,
        name="Escenari Cel",
        scenario_type="cel",
        probability="BAIXA",
        possibility="CONDICIONAL",
    )
    merged = merge_scenario_with_justification(
        sc,
        {
            "base_probability_pct": 10,
            "estimated_probability_pct": 18,
            "adjustment_points": 8,
            "rationale": "Test",
            "supporting_signals": [],
            "contradicting_signals": [],
        },
    )
    assert merged["possibility"] == "CONDICIONAL"
    assert merged["estimated_probability_pct"] == 18
