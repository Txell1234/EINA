"""Tests for scenario milestone parsing and persistence."""
import pytest

from services.scenario_milestone_service import (
    parse_milestones_from_narrative,
    persist_milestones_for_scenario,
    create_monitors_from_milestones,
)


@pytest.mark.unit
def test_parse_milestones_from_arrow_indicators():
    narrative = """
    Seqüència temporal:
    Any 1: consolidació inicial
    → Augment de la despesa de defensa japonesa per sobre del 2% del PIB
    → Nova declaració oficial sobre l'Article 9
    Anys 2-3:
    → Acord de cooperació militar amb aliats de l'Indo-Pacífic
    """
    items = parse_milestones_from_narrative(narrative)
    assert len(items) >= 2
    assert any("defensa" in (i["title"] or "").lower() for i in items)
    assert items[0]["order_index"] == 0


@pytest.mark.unit
def test_parse_milestones_reversibility():
    narrative = "→ Reforma constitucional irreversible del marc de defensa"
    items = parse_milestones_from_narrative(narrative)
    assert len(items) == 1
    assert items[0]["reversibility"] == "low"


@pytest.mark.unit
async def test_persist_milestones(db_session, sample_case):
    from models.prospective import ProspectiveProject, ProspectiveScenario

    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Milestones test",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()
    sc = ProspectiveScenario(
        project_id=project.id,
        name="Escenari Tensió",
        scenario_type="tensio",
        narrative="→ Sancions econòmiques contra el sector energètic\n→ Nova trobada diplomàtica",
    )
    db_session.add(sc)
    await db_session.commit()
    await db_session.refresh(sc)

    saved = await persist_milestones_for_scenario(db_session, sc.id, sc.narrative or "")
    assert len(saved) >= 1

    again = await persist_milestones_for_scenario(db_session, sc.id, sc.narrative or "")
    assert len(again) == len(saved)


@pytest.mark.unit
async def test_create_monitors_from_milestones(db_session, sample_case):
    from models.prospective import ProspectiveProject, ProspectiveScenario

    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Monitor milestones",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()
    sc = ProspectiveScenario(
        project_id=project.id,
        name="Escenari Infern",
        scenario_type="infern",
        narrative="→ Crisis oberta en el estret de Taiwan amb mobilització naval",
    )
    db_session.add(sc)
    await db_session.commit()
    await db_session.refresh(sc)

    await persist_milestones_for_scenario(db_session, sc.id, sc.narrative or "")
    created = await create_monitors_from_milestones(db_session, project.id, sc.id)
    assert len(created) >= 1
