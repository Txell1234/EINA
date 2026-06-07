"""Tests for inquiry dashboard service."""
import pytest
from datetime import datetime, timedelta, timezone

from services.inquiry_dashboard_service import (
    InquiryDashboardService,
    extract_probability_history,
    probability_delta,
)


@pytest.mark.unit
def test_extract_probability_history_from_audit():
    artifacts = {
        "audit_trail": [
            {"event": "run_started", "run_number": 1},
            {"event": "synthesis_completed", "run_number": 1, "probability_pct": 30, "at": "2026-01-01T00:00:00Z"},
            {"event": "synthesis_completed", "run_number": 2, "probability_pct": 42, "at": "2026-01-02T00:00:00Z"},
        ]
    }
    hist = extract_probability_history(artifacts, current_probability=42)
    assert len(hist) == 2
    assert hist[0]["probability_pct"] == 30
    assert hist[1]["probability_pct"] == 42
    assert probability_delta(hist) == 12.0


@pytest.mark.unit
async def test_list_dashboard_stats(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry

    past = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.add_all(
        [
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Trump announces US blockade of Hormuz lifted by December 2026?",
                mode="lite",
                status="completed",
                answer={"probability_pct": 35, "possibility": "PLAUSIBLE"},
            ),
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Israel and Indonesia normalize relations by 2027?",
                mode="full",
                status="awaiting_godet",
                auto_rerun_enabled=1,
                next_rerun_at=past,
            ),
        ]
    )
    await db_session.commit()

    result = await InquiryDashboardService(db_session).list_dashboard()
    assert result["found"] is True
    assert result["stats"]["total"] == 2
    assert result["stats"]["completed"] == 1
    assert result["stats"]["awaiting_godet"] == 1
    assert result["stats"]["scheduled_due"] == 1
    assert len(result["items"]) == 2


@pytest.mark.unit
async def test_list_dashboard_search_and_filters(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry

    db_session.add_all(
        [
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Trump announces US blockade of Hormuz lifted by December 2026?",
                mode="lite",
                status="completed",
                parsed_trigger={"parse_confidence": 0.92, "llm_used": True},
                answer={"probability_pct": 35},
            ),
            ProspectiveInquiry(
                case_id=sample_case.id,
                question="Israel and Indonesia normalize relations by 2027?",
                mode="full",
                status="completed",
                parsed_trigger={"parse_confidence": 0.55, "llm_used": False},
                answer={"probability_pct": 20},
            ),
        ]
    )
    await db_session.commit()

    svc = InquiryDashboardService(db_session)
    by_q = await svc.list_dashboard(search="Hormuz")
    assert by_q["count"] == 1
    assert "Hormuz" in by_q["items"][0]["question"]

    lite = await svc.list_dashboard(mode="lite")
    assert lite["count"] == 1
    assert lite["items"][0]["mode"] == "lite"

    llm = await svc.list_dashboard(llm_only=True)
    assert llm["count"] == 1
    assert llm["items"][0]["llm_used"] is True

    conf = await svc.list_dashboard(min_confidence=0.8)
    assert conf["count"] == 1
    assert conf["items"][0]["parse_confidence"] == 0.92


@pytest.mark.unit
async def test_batch_schedule(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry

    rows = [
        ProspectiveInquiry(
            case_id=sample_case.id,
            question="Trump announces US blockade of Hormuz lifted by December 2026?",
            mode="lite",
            status="completed",
        ),
        ProspectiveInquiry(
            case_id=sample_case.id,
            question="Israel and Indonesia normalize relations by 2027?",
            mode="full",
            status="completed",
            auto_rerun_enabled=1,
            rerun_interval_hours=12,
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()
    await db_session.refresh(rows[0])
    await db_session.refresh(rows[1])

    svc = InquiryDashboardService(db_session)
    enable = await svc.batch_schedule([rows[0].id, rows[1].id], enabled=True, interval_hours=48)
    assert enable["ok_count"] == 2
    assert enable["failed_count"] == 0

    disable = await svc.batch_schedule([rows[0].id], enabled=False)
    assert disable["ok_count"] == 1


@pytest.mark.unit
async def test_export_batch_zip(db_session, sample_case):
    from models.prospective_inquiry import ProspectiveInquiry

    inquiry = ProspectiveInquiry(
        case_id=sample_case.id,
        question="Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
        status="completed",
        answer={"probability_pct": 40},
    )
    db_session.add(inquiry)
    await db_session.commit()
    await db_session.refresh(inquiry)

    payload = await InquiryDashboardService(db_session).export_batch_zip([inquiry.id])
    assert payload[:2] == b"PK"
    assert len(payload) > 100
