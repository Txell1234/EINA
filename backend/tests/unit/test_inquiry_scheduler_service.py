"""Tests for inquiry scheduler."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from observability.inquiry_job_queue import reset_inquiry_job_queue_singleton
from services.inquiry_orchestrator_service import InquiryOrchestratorService
from services.inquiry_scheduler_service import InquirySchedulerService


@pytest.fixture(autouse=True)
def _fresh_inquiry_job_queue(monkeypatch):
    monkeypatch.setenv("INQUIRY_JOB_QUEUE_BACKEND", "memory")
    from app.config import settings

    settings.INQUIRY_JOB_QUEUE_BACKEND = "memory"
    settings.REDIS_URL = ""
    reset_inquiry_job_queue_singleton()
    yield
    reset_inquiry_job_queue_singleton()

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


@pytest.mark.unit
async def test_enqueue_due_batch(db_session, sample_case):
    svc = InquiryOrchestratorService(db_session)
    row = await svc.create_inquiry(
        sample_case.id,
        "NATO expands Arctic monitoring by 2028?",
        mode="lite",
    )
    row.status = "completed"
    row.auto_rerun_enabled = 1
    row.rerun_interval_hours = 24
    row.next_rerun_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db_session.commit()

    summary = await InquirySchedulerService(db_session).enqueue_due_batch(limit=5)
    assert summary["due"] >= 1
    assert summary["enqueued"] >= 1
    assert summary["queue_enabled"] is True

    dup = await InquirySchedulerService(db_session).enqueue_due_batch(limit=5)
    assert dup["skipped_duplicate"] >= 1


@pytest.mark.unit
async def test_process_next_jobs(db_session, sample_case):
    sched = InquirySchedulerService(db_session)
    orch = InquiryOrchestratorService(db_session)
    row = await orch.create_inquiry(
        sample_case.id,
        "EU carbon border tax expanded by 2027?",
        mode="lite",
    )
    row.status = "completed"
    row.auto_rerun_enabled = 1
    row.rerun_interval_hours = 24
    row.next_rerun_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    await db_session.commit()

    enq = await sched.enqueue_due_batch(limit=5)
    assert enq["enqueued"] >= 1

    with patch.object(
        InquiryOrchestratorService,
        "run_batch",
        new=AsyncMock(return_value={"status": "completed", "steps": 3}),
    ):
        summary = await sched.process_next_jobs(limit=1)

    assert summary["processed"] == 1
    assert summary["ok_count"] == 1
    assert summary["results"][0]["inquiry_id"] == row.id


@pytest.mark.unit
async def test_run_due_batch_inline(monkeypatch, db_session, sample_case):
    monkeypatch.setenv("INQUIRY_JOB_QUEUE_BACKEND", "inline")
    from app.config import settings

    settings.INQUIRY_JOB_QUEUE_BACKEND = "inline"
    reset_inquiry_job_queue_singleton()

    sched = InquirySchedulerService(db_session)
    orch = InquiryOrchestratorService(db_session)
    row = await orch.create_inquiry(
        sample_case.id,
        "Japan reopens nuclear exports by 2029?",
        mode="lite",
    )
    row.status = "completed"
    row.auto_rerun_enabled = 1
    row.rerun_interval_hours = 24
    row.next_rerun_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db_session.commit()

    with patch.object(
        InquiryOrchestratorService,
        "run_batch",
        new=AsyncMock(return_value={"status": "completed"}),
    ):
        summary = await sched.run_due_batch(limit=3)

    assert summary["mode"] == "inline"
    assert summary["processed"] >= 1
    assert summary["results"][0]["inquiry_id"] == row.id
