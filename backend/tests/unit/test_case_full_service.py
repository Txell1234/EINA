"""Tests for case full bundle loader."""
import pytest

from models.ai_analysis import AIAnalysis
from models.osint import OSINTQuery, OSINTResult, QueryStatus
from services.case_full_service import load_case_full_bundle


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_case_full_bundle_empty(db_session, sample_case):
    bundle = await load_case_full_bundle(db_session, sample_case.id)
    assert bundle["counts"]["osint_queries"] == 0
    assert bundle["osint_data"] == []
    assert bundle["ai_analyses"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_case_full_bundle_with_osint(db_session, sample_case):
    query = OSINTQuery(
        query_type="gdelt",
        query_params={"query": "test"},
        case_id=sample_case.id,
        status=QueryStatus.COMPLETED,
    )
    db_session.add(query)
    await db_session.commit()
    await db_session.refresh(query)

    result = OSINTResult(
        query_id=query.id,
        data={"status": "success", "data": [{"id": 1}]},
        status="completed",
    )
    db_session.add(result)
    await db_session.commit()

    bundle = await load_case_full_bundle(db_session, sample_case.id)
    assert bundle["counts"]["osint_queries"] == 1
    assert bundle["osint_data"][0]["query_type"] == "gdelt"
    assert bundle["osint_data"][0]["result_id"] == result.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_case_full_bundle_with_ai(db_session, sample_case):
    db_session.add(
        AIAnalysis(
            case_id=sample_case.id,
            analysis_type="taranis",
            analysis_data={"ok": True},
            confidence_score=0.8,
        )
    )
    await db_session.commit()

    bundle = await load_case_full_bundle(db_session, sample_case.id)
    assert bundle["counts"]["ai_analyses"] == 1
    assert bundle["ai_analyses"][0]["analysis_type"] == "taranis"
