"""Tests for company registry aggregation."""
import pytest

from models.prospective import ProspectiveActor, ProspectiveProject
from services.company_registry_service import load_company_registry


@pytest.mark.asyncio
async def test_load_company_registry_reference_profiles(db_session, sample_case):
    sample_case.description = "Japanese rearmament and defense budget Indo-Pacific"
    sample_case.name = "Japan Defense"
    await db_session.commit()

    reg = await load_company_registry(db_session, sample_case.id)
    assert reg["found"] is True
    assert reg["summary"]["total"] >= 1
    names = {c["name"] for c in reg["companies"]}
    assert any("Mitsubishi" in n or "Lockheed" in n for n in names)


@pytest.mark.asyncio
async def test_load_company_registry_godet_actors(db_session, sample_case):
    sample_case.description = "Defense industry analysis"
    await db_session.commit()

    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Godet Test",
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(
        ProspectiveActor(
            project_id=project.id,
            code="A1",
            name="Lockheed Martin",
            strategic_goals=["Expand market entry in Indo-Pacific"],
            force_score=4.0,
        )
    )
    await db_session.commit()

    reg = await load_company_registry(db_session, sample_case.id, project_id=project.id)
    names = {c["name"] for c in reg["companies"]}
    assert "Lockheed Martin" in names
    assert reg["summary"]["from_godet"] >= 1


@pytest.mark.asyncio
async def test_load_company_registry_not_found_case(db_session):
    reg = await load_company_registry(db_session, 999999)
    assert reg["found"] is False
