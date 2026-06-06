"""Tests for EnsembleData OSINT dispatch."""
import pytest
from unittest.mock import AsyncMock, patch

from integrations.ensembledata_osint import execute_ensembledata_query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_ensembledata_tiktok_keyword():
    with patch("integrations.ensembledata_osint.EnsembleDataAPIService") as mock_cls:
        inst = mock_cls.return_value
        inst.tiktok_keyword_posts = AsyncMock(
            return_value={"status": "success", "data": [{"id": 1}]},
        )
        result = await execute_ensembledata_query(
            "ensembledata_tiktok_keyword_posts",
            {"query": "Hormuz", "max_results": 10},
        )
    assert result["status"] == "success"
    inst.tiktok_keyword_posts.assert_awaited_once_with("Hormuz", 10)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_ensembledata_unknown_type():
    result = await execute_ensembledata_query("ensembledata_unknown_x", {})
    assert result["status"] == "error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_osint_service_routes_ensembledata(db_session, sample_case):
    from services.osint_service import OSINTService

    with patch(
        "integrations.ensembledata_osint.execute_ensembledata_query",
        new_callable=AsyncMock,
        return_value={"status": "success", "data": []},
    ) as mock_exec:
        svc = OSINTService(db_session)
        out = await svc.execute_query(
            "ensembledata_twitter_user_tweets",
            {"username": "Reuters", "count": 5},
            case_id=sample_case.id,
        )
    mock_exec.assert_awaited_once()
    assert out.get("status") == "completed" or out.get("query_id")
