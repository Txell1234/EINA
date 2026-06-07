"""Standalone worker for inquiry rerun jobs (Redis queue).

Usage:
  python -m scripts.inquiry_worker

Requires INQUIRY_WORKER_MODE=standalone on the API and Redis (or memory queue for dev).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import AsyncSessionLocal, init_db
from observability.inquiry_job_queue import get_inquiry_job_queue, is_inquiry_job_queue_enabled
from observability.logging_config import setup_structured_logging
from services.inquiry_scheduler_service import InquirySchedulerService

if settings.STRUCTURED_LOGGING:
    setup_structured_logging()

logger = logging.getLogger(__name__)


async def run_worker_loop() -> None:
    if not is_inquiry_job_queue_enabled():
        logger.error("Inquiry job queue disabled (INQUIRY_JOB_QUEUE_BACKEND=inline)")
        return

    queue = get_inquiry_job_queue()
    if queue is None:
        logger.error("Inquiry job queue unavailable")
        return

    logger.info(
        "Inquiry worker started (batch=%s, dequeue_timeout=%ss)",
        settings.INQUIRY_WORKER_BATCH_SIZE,
        settings.INQUIRY_WORKER_DEQUEUE_TIMEOUT_SECONDS,
    )

    while True:
        try:
            async with AsyncSessionLocal() as db:
                summary = await InquirySchedulerService(db).process_next_jobs(
                    limit=settings.INQUIRY_WORKER_BATCH_SIZE,
                    dequeue_timeout=settings.INQUIRY_WORKER_DEQUEUE_TIMEOUT_SECONDS,
                )
            if summary.get("processed"):
                logger.info(
                    "Inquiry worker: processed=%s ok=%s failed=%s",
                    summary.get("processed"),
                    summary.get("ok_count"),
                    summary.get("failed_count"),
                )
            elif summary.get("processed", 0) == 0:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Inquiry worker error: %s", exc)
            await asyncio.sleep(5.0)


async def main() -> None:
    await init_db()
    await run_worker_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Inquiry worker stopped")
