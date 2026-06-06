"""Tests for inquiry scheduler."""
import pytest
from datetime import datetime, timedelta, timezone

from services.inquiry_orchestrator_service import InquiryOrchestratorService
from services.inquiry_scheduler_service import InquirySchedulerService


@pytest.mark.unit
async def test_set_schedule(db_session, sample_case):
    svc = InquiryOrchestratorService(db_session)
    row = await svc.create_inquiry(
        sample_case.id,
        "Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
    )
    result = await svc.set_schedule(row.id, enabled=True, interval_hours=12)
    assert result["ok"] is True
    assert result["auto_rerun_enabled"] is True
    assert result["next_rerun_at"] is not None


@pytest.mark.unit
async def test_list_due_inquiry(db_session, sample_case):
    svc = InquiryOrchestratorService(db_session)
    row = await svc.create_inquiry(
        sample_case.id,
        "Israel and Indonesia normalize relations by 2027?",
        mode="lite",
    )
    row.status = "completed"
    row.auto_rerun_enabled = 1
    row.rerun_interval_hours = 24
    row.next_rerun_at = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    due = await InquirySchedulerService(db_session).list_due()
    assert any(i.id == row.id for i in due)
