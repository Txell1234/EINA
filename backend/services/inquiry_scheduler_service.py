"""Scheduled re-run of prospective inquiries (additive, no Temporal)."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective_inquiry import ProspectiveInquiry
from observability.inquiry_job_queue import get_inquiry_job_queue, is_inquiry_job_queue_enabled
from observability.metrics import INQUIRY_JOB_DURATION_SECONDS

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

    async def enqueue_due_batch(self, *, limit: int = 10) -> dict[str, Any]:
        queue = get_inquiry_job_queue()
        if queue is None:
            return {"due": 0, "enqueued": 0, "skipped_duplicate": 0, "queue_enabled": False}

        due = await self.list_due(limit=limit)
        enqueued = 0
        skipped = 0
        for inquiry in due:
            ok = await queue.enqueue(
                inquiry.id,
                "scheduled_rerun",
                force_refresh=True,
            )
            if ok:
                enqueued += 1
            else:
                skipped += 1

        return {
            "due": len(due),
            "enqueued": enqueued,
            "skipped_duplicate": skipped,
            "queue_enabled": True,
        }

    async def process_job(self, job: dict[str, Any]) -> dict[str, Any]:
        from services.inquiry_orchestrator_service import InquiryOrchestratorService

        job_type = job.get("job_type", "scheduled_rerun")
        inquiry_id = int(job["inquiry_id"])
        force_refresh = bool(job.get("force_refresh", True))
        started = time.perf_counter()

        orchestrator = InquiryOrchestratorService(self.db)
        try:
            summary = await orchestrator.run_batch(inquiry_id, force_refresh=force_refresh)
            INQUIRY_JOB_DURATION_SECONDS.labels(job_type=job_type).observe(
                time.perf_counter() - started
            )
            return {"inquiry_id": inquiry_id, "ok": True, **summary}
        except Exception as exc:
            INQUIRY_JOB_DURATION_SECONDS.labels(job_type=job_type).observe(
                time.perf_counter() - started
            )
            logger.warning("Inquiry job failed for inquiry %s: %s", inquiry_id, exc)
            return {"inquiry_id": inquiry_id, "ok": False, "error": str(exc)[:200]}

    async def process_next_jobs(
        self,
        *,
        limit: int = 5,
        dequeue_timeout: float = 0.0,
    ) -> dict[str, Any]:
        queue = get_inquiry_job_queue()
        if queue is None:
            return {"processed": 0, "results": [], "queue_enabled": False}

        results: list[dict[str, Any]] = []
        for _ in range(limit):
            job = await queue.dequeue(timeout=dequeue_timeout if _ == 0 else 0.0)
            if not job:
                break
            result = await self.process_job(job)
            if result.get("ok"):
                await queue.complete(job)
            else:
                await queue.fail(job, result.get("error", "unknown"))
            results.append(result)

        return {
            "processed": len(results),
            "ok_count": sum(1 for r in results if r.get("ok")),
            "failed_count": sum(1 for r in results if not r.get("ok")),
            "results": results,
            "queue_enabled": True,
        }

    async def run_due_batch(self, *, limit: int = 5) -> dict[str, Any]:
        if is_inquiry_job_queue_enabled():
            enqueue_summary = await self.enqueue_due_batch(limit=max(limit * 2, 10))
            process_summary = await self.process_next_jobs(limit=limit)
            return {
                **enqueue_summary,
                **process_summary,
                "mode": "queue",
            }

        from services.inquiry_orchestrator_service import InquiryOrchestratorService

        due = await self.list_due(limit=limit)
        if not due:
            return {"due": 0, "processed": 0, "results": [], "mode": "inline"}

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
            "ok_count": sum(1 for r in results if r.get("ok")),
            "failed_count": sum(1 for r in results if not r.get("ok")),
            "results": results,
            "mode": "inline",
        }

    @staticmethod
    def compute_next_rerun(interval_hours: int) -> datetime:
        hours = max(1, min(interval_hours, 168))
        return datetime.now(timezone.utc) + timedelta(hours=hours)
