"""Tests for godet_checklist_service."""
import pytest

from services.godet_checklist_service import GODET_STEP_ORDER, project_godet_checklist


@pytest.mark.asyncio
async def test_project_godet_checklist_missing(db_session, sample_case):
    from models.prospective import ProspectiveProject

    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Hub test",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    meta = await project_godet_checklist(db_session, project.id)
    assert meta["found"] is True
    assert meta["checklist"]["project"] is True
    assert meta["checklist"]["variables"] is False
    assert meta["suggested_next_step"] == "variables"
    assert "variables" in meta["missing_steps"]


@pytest.mark.asyncio
async def test_project_godet_checklist_not_found(db_session):
    meta = await project_godet_checklist(db_session, 999999)
    assert meta["found"] is False
    assert meta["missing_steps"] == list(GODET_STEP_ORDER)
