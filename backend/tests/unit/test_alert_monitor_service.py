"""
Unit tests for AlertMonitorService
"""
from unittest.mock import AsyncMock, patch

import pytest

from models.prospective import AlertMatch, AlertMonitor, ProspectiveProject
from services import alert_monitor_service as ams


@pytest.mark.unit
def test_keywords_extracts_terms():
    text = "Augment de la presència militar a Catalunya i conflicte regional"
    kws = ams._keywords(text)
    assert isinstance(kws, list)
    assert len(kws) <= 4
    assert any("Catalunya" in k or "catalunya" in k.lower() for k in kws)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_monitors_empty(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Projecte prova",
        hypothesis="H1",
        context="Ctx",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    rows = await ams.list_monitors(db_session, project.id)
    assert rows == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_monitors_from_scenario(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Monitor test",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    narrative = (
        "Escenari pessimista:\n"
        "→ Augment de sancions econòmiques contra el sector energètic\n"
        "→ Nova declaració oficial del govern central\n"
    )
    created = await ams.create_monitors_from_scenario(
        db_session, project.id, scenario_id=None, narrative=narrative
    )
    assert len(created) >= 1
    assert all("indicator" in c and "keywords" in c for c in created)

    listed = await ams.list_monitors(db_session, project.id)
    assert len(listed) == len(created)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_all_active_monitors(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Run all",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(
        AlertMonitor(
            project_id=project.id,
            indicator="Indicador de prova per monitor actiu",
            keywords=["prova", "monitor"],
            osint_sources=["gdelt"],
            is_active=1,
        )
    )
    await db_session.commit()

    mock_osint = AsyncMock()
    mock_osint.execute_query = AsyncMock(
        return_value={"data": {"count": 2, "articles": []}}
    )

    with patch("services.osint_service.OSINTService", return_value=mock_osint):
        result = await ams.run_all_active_monitors(db_session)

    assert result["checked"] == 1
    assert result["results"][0]["new_matches"] == 0
    assert result["results"][0]["total_unique_matches"] >= 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_monitor_check_skips_inactive(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Inactive",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    monitor = AlertMonitor(
        project_id=project.id,
        indicator="Monitor inactiu de prova llarg",
        keywords=["test"],
        is_active=0,
    )
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    result = await ams.run_monitor_check(db_session, monitor.id)
    assert result["status"] == "skipped"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_triggered_summary(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Summary test",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(
        AlertMonitor(
            project_id=project.id,
            indicator="Monitor sense coincidències",
            keywords=["quiet"],
            is_active=1,
            match_count=0,
        )
    )
    triggered_monitor = AlertMonitor(
        project_id=project.id,
        indicator="Monitor amb coincidències OSINT detectades",
        keywords=["alerta"],
        is_active=1,
        match_count=5,
        case_id=sample_case.id,
    )
    db_session.add(triggered_monitor)
    await db_session.flush()
    db_session.add(
        AlertMatch(
            monitor_id=triggered_monitor.id,
            project_id=project.id,
            case_id=sample_case.id,
            title="Article OSINT de prova",
            url="https://example.com/osint-alert",
            excerpt="Alerta detectada amb paraules clau",
            source_type="gdelt",
            matched_keywords=["alerta"],
            match_score=0.8,
            status="new",
        )
    )
    await db_session.commit()

    summary = await ams.list_triggered_summary(db_session, case_id=sample_case.id)
    assert summary["total_monitors"] == 2
    assert summary["triggered_count"] == 1
    assert summary["total_matches"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_repair_monitor_counts_fixes_stale(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Repair counts",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    monitor = AlertMonitor(
        project_id=project.id,
        indicator="Indicador amb comptador fantasma",
        keywords=["test"],
        is_active=1,
        match_count=90,
        unread_count=10,
    )
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    repaired = await ams.repair_monitor_counts(db_session, monitor_id=monitor.id)
    assert repaired == 1
    await db_session.refresh(monitor)
    assert monitor.match_count == 0
    assert monitor.unread_count == 0
