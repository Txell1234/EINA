"""Scheduled re-run of prospective inquiries (additive, no Temporal)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective_inquiry import ProspectiveInquiry

logger = logging.getLogger(__name__)


class InquirySchedulerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_due(self, *, limit: int = 10) -> list[ProspectiveInquiry]:
        now = datetime.now(timezone.utc)
        r = await self.db.execute(
            select(ProspectiveInquiry)
            .where(
                ProspectiveInquiry.auto_rerun_enabled == 1,
                ProspectiveInquiry.next_rerun_at.isnot(None),
                ProspectiveInquiry.next_rerun_at <= now,
                ProspectiveInquiry.status.in_(("completed", "awaiting_godet", "failed")),
            )
            .order_by(ProspectiveInquiry.next_rerun_at.asc())
            .limit(limit)
        )
        return list(r.scalars().all())

    async def run_due_batch(self, *, limit: int = 5) -> dict[str, Any]:
        from services.inquiry_orchestrator_service import InquiryOrchestratorService

        due = await self.list_due(limit=limit)
        if not due:
            return {"due": 0, "processed": 0, "results": []}

        orchestrator = InquiryOrchestratorService(self.db)
        results: list[dict[str, Any]] = []
        for inquiry in due:
            try:
                summary = await orchestrator.run_batch(inquiry.id, force_refresh=True)
                results.append({"inquiry_id": inquiry.id, "ok": True, **summary})
            except Exception as exc:
                logger.warning("Scheduled rerun failed for inquiry %s: %s", inquiry.id, exc)
                results.append({"inquiry_id": inquiry.id, "ok": False, "error": str(exc)[:200]})

        return {
            "due": len(due),
            "processed": len(results),
            "results": results,
        }

    @staticmethod
    def compute_next_rerun(interval_hours: int) -> datetime:
        hours = max(1, min(interval_hours, 168))
        return datetime.now(timezone.utc) + timedelta(hours=hours)
