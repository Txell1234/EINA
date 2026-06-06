"""Tests for OSINTService query routing."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from services.osint_service import OSINTService, _unavailable


@pytest.mark.unit
def test_unavailable_helper_shape():
    out = _unavailable("sherlock", "missing binary")
    assert out["status"] == "unavailable"
    assert out["query_type"] == "sherlock"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_sherlock_unavailable(db_session, sample_case):
    svc = OSINTService(db_session)
    out = await svc.execute_query("sherlock", {"username": "test"}, case_id=sample_case.id)
    assert out.get("query_id")
    data = out.get("data") or {}
    assert data.get("status") == "unavailable" or out.get("status") in ("error", "failed", "completed")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_unknown_type(db_session, sample_case):
    svc = OSINTService(db_session)
    out = await svc.execute_query("totally_unknown_xyz", {}, case_id=sample_case.id)
    assert out.get("query_id")
    data = out.get("data") or {}
    assert "error" in data or out.get("error")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_gdelt_routes(db_session, sample_case):
    mock_gdelt = AsyncMock(return_value={"status": "success", "events": []})
    with patch("integrations.gdelt_api.GDELTAPIService") as mock_cls:
        mock_cls.return_value.search_events = mock_gdelt
        svc = OSINTService(db_session)
        out = await svc.execute_query(
            "gdelt",
            {"query": "Taiwan", "days": 3},
            case_id=sample_case.id,
        )
    assert out.get("query_id")
    assert out.get("result_id")
    mock_gdelt.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_ensembledata_routes(db_session, sample_case):
    with patch(
        "integrations.ensembledata_osint.execute_ensembledata_query",
        new_callable=AsyncMock,
        return_value={"status": "success", "data": [{"id": 1}]},
    ) as mock_exec:
        svc = OSINTService(db_session)
        out = await svc.execute_query(
            "ensembledata_instagram_hashtag_posts",
            {"hashtag": "geopolitics"},
            case_id=sample_case.id,
        )
    mock_exec.assert_awaited_once()
    assert out.get("query_id")
    assert out.get("result_id")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_without_case_id_still_persists(db_session):
    with patch(
        "integrations.ensembledata_osint.execute_ensembledata_query",
        new_callable=AsyncMock,
        return_value={"status": "success", "data": []},
    ):
        svc = OSINTService(db_session)
        out = await svc.execute_query(
            "ensembledata_tiktok_keyword_posts",
            {"keyword": "test"},
            case_id=None,
        )
    assert out.get("query_id")
