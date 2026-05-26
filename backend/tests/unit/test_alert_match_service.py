"""Tests for alert match persistence."""
from unittest.mock import AsyncMock, patch

import pytest

from models.prospective import AlertMatch, AlertMonitor, ProspectiveProject
from services import alert_monitor_service as ams


@pytest.mark.unit
def test_match_article_keywords():
    article = {"title": "China naval presence increases", "summary": "South China Sea tension"}
    matched, score = ams._match_article(article, ["China", "naval"])
    assert "China" in matched or "naval" in matched
    assert score > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_monitor_persists_matches(db_session, sample_case):
    project = ProspectiveProject(
        case_id=sample_case.id,
        title="Match persist",
        hypothesis="H",
        context="C",
    )
    db_session.add(project)
    await db_session.flush()

    monitor = AlertMonitor(
        project_id=project.id,
        case_id=sample_case.id,
        indicator="Augment presència naval xinesa al Mar de la Xina Meridional",
        keywords=["China", "naval", "South"],
        osint_sources=["gdelt"],
        is_active=1,
    )
    db_session.add(monitor)
    await db_session.commit()
    await db_session.refresh(monitor)

    mock_osint = AsyncMock()
    mock_osint.execute_query = AsyncMock(
        return_value={
            "query_id": 1,
            "result_id": 2,
            "data": {
                "articles": [
                    {
                        "title": "China expands naval drills",
                        "url": "https://example.com/china-naval",
                        "summary": "Naval presence increases in contested waters",
                        "date": "2026-05-18",
                    }
                ]
            },
        }
    )

    with patch("services.osint_service.OSINTService", return_value=mock_osint):
        result = await ams.run_monitor_check(db_session, monitor.id)

    assert result["new_matches"] >= 1
    rows = (
        await db_session.execute(
            __import__("sqlalchemy").select(AlertMatch).where(AlertMatch.monitor_id == monitor.id)
        )
    ).scalars().all()
    assert len(rows) >= 1
    assert rows[0].url == "https://example.com/china-naval"
    assert rows[0].matched_keywords
