"""Tests for inquiry dashboard service."""
import pytest
from datetime import datetime, timedelta, timezone

from services.inquiry_dashboard_service import InquiryDashboardService


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
