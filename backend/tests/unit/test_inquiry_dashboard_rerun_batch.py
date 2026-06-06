"""Tests for inquiry dashboard batch rerun."""
import pytest

from services.inquiry_dashboard_service import InquiryDashboardService
from services.inquiry_orchestrator_service import InquiryOrchestratorService


@pytest.mark.unit
async def test_rerun_batch_empty_raises(db_session):
    svc = InquiryDashboardService(db_session)
    with pytest.raises(ValueError, match="Calen IDs"):
        await svc.rerun_batch([])


@pytest.mark.unit
async def test_rerun_batch_too_many_raises(db_session):
    svc = InquiryDashboardService(db_session)
    with pytest.raises(ValueError, match="Màxim"):
        await svc.rerun_batch(list(range(1, 12)))


@pytest.mark.unit
async def test_rerun_batch_calls_orchestrator(db_session, sample_case, monkeypatch):
    calls: list[int] = []

    async def fake_run_batch(self, inquiry_id, *, force_refresh=True):
        calls.append(inquiry_id)
        return {"status": "completed", "event": "done", "inquiry_id": inquiry_id}

    monkeypatch.setattr(InquiryOrchestratorService, "run_batch", fake_run_batch)

    orch = InquiryOrchestratorService(db_session)
    row = await orch.create_inquiry(
        sample_case.id,
        "Trump announces US blockade of Hormuz lifted by December 2026?",
        mode="lite",
    )

    result = await InquiryDashboardService(db_session).rerun_batch([row.id])
    assert result["processed"] == 1
    assert result["ok_count"] == 1
    assert calls == [row.id]
