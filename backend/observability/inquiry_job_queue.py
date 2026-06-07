"""Pluggable job queue for inquiry reruns (Redis or in-memory fallback)."""
from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from observability.metrics import record_inquiry_job_operation, set_inquiry_job_queue_depth

logger = logging.getLogger(__name__)

QUEUE_LIST_KEY = "q2fs:inquiry_jobs:queue"
PENDING_SET_KEY = "q2fs:inquiry_jobs:pending"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InquiryJobQueueBackend(ABC):
    @abstractmethod
    async def enqueue(
        self,
        inquiry_id: int,
        job_type: str = "scheduled_rerun",
        *,
        force_refresh: bool = True,
        meta: dict[str, Any] | None = None,
    ) -> bool:
        """Enqueue a job. Returns False if inquiry already pending (deduped)."""

    @abstractmethod
    async def dequeue(self, *, timeout: float = 0.0) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def complete(self, job: dict[str, Any]) -> None:
        ...

    @abstractmethod
    async def fail(self, job: dict[str, Any], error: str) -> None:
        ...

    @abstractmethod
    async def stats(self) -> dict[str, Any]:
        ...

    def _build_job(
        self,
        inquiry_id: int,
        job_type: str,
        *,
        force_refresh: bool,
        meta: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "job_id": str(uuid.uuid4()),
            "inquiry_id": inquiry_id,
            "job_type": job_type,
            "force_refresh": force_refresh,
            "enqueued_at": _utc_now_iso(),
            "meta": meta or {},
        }


class MemoryInquiryJobQueue(InquiryJobQueueBackend):
    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque()
        self._pending: set[int] = set()

    async def enqueue(
        self,
        inquiry_id: int,
        job_type: str = "scheduled_rerun",
        *,
        force_refresh: bool = True,
        meta: dict[str, Any] | None = None,
    ) -> bool:
        if inquiry_id in self._pending:
            record_inquiry_job_operation("enqueue", job_type, status="deduped")
            await self._refresh_depth()
            return False
        job = self._build_job(
            inquiry_id,
            job_type,
            force_refresh=force_refresh,
            meta=meta,
        )
        self._pending.add(inquiry_id)
        self._queue.append(job)
        record_inquiry_job_operation("enqueue", job_type, status="ok")
        await self._refresh_depth()
        return True

    async def dequeue(self, *, timeout: float = 0.0) -> dict[str, Any] | None:
        _ = timeout
        if not self._queue:
            return None
        job = self._queue.popleft()
        await self._refresh_depth()
        return job

    async def complete(self, job: dict[str, Any]) -> None:
        self._pending.discard(int(job["inquiry_id"]))
        record_inquiry_job_operation(
            "complete",
            job.get("job_type", "scheduled_rerun"),
            status="ok",
        )
        await self._refresh_depth()

    async def fail(self, job: dict[str, Any], error: str) -> None:
        _ = error
        self._pending.discard(int(job["inquiry_id"]))
        record_inquiry_job_operation(
            "complete",
            job.get("job_type", "scheduled_rerun"),
            status="failed",
        )
        await self._refresh_depth()

    async def stats(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "queued": len(self._queue),
            "pending": len(self._pending),
        }

    async def _refresh_depth(self) -> None:
        set_inquiry_job_queue_depth(len(self._queue), len(self._pending))


class RedisInquiryJobQueue(InquiryJobQueueBackend):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, decode_responses=True)

    async def enqueue(
        self,
        inquiry_id: int,
        job_type: str = "scheduled_rerun",
        *,
        force_refresh: bool = True,
        meta: dict[str, Any] | None = None,
    ) -> bool:
        added = await self._redis.sadd(PENDING_SET_KEY, str(inquiry_id))
        if not added:
            record_inquiry_job_operation("enqueue", job_type, status="deduped")
            await self._refresh_depth()
            return False
        job = self._build_job(
            inquiry_id,
            job_type,
            force_refresh=force_refresh,
            meta=meta,
        )
        body = json.dumps(job, ensure_ascii=False)
        await self._redis.rpush(QUEUE_LIST_KEY, body)
        record_inquiry_job_operation("enqueue", job_type, status="ok")
        await self._refresh_depth()
        return True

    async def dequeue(self, *, timeout: float = 0.0) -> dict[str, Any] | None:
        if timeout > 0:
            result = await self._redis.brpop(QUEUE_LIST_KEY, timeout=max(1, int(timeout)))
            if not result:
                return None
            raw = result[1]
        else:
            raw = await self._redis.lpop(QUEUE_LIST_KEY)
            if not raw:
                return None
        try:
            job = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid inquiry job payload in queue")
            return None
        await self._refresh_depth()
        return job

    async def complete(self, job: dict[str, Any]) -> None:
        await self._redis.srem(PENDING_SET_KEY, str(job["inquiry_id"]))
        record_inquiry_job_operation(
            "complete",
            job.get("job_type", "scheduled_rerun"),
            status="ok",
        )
        await self._refresh_depth()

    async def fail(self, job: dict[str, Any], error: str) -> None:
        _ = error
        await self._redis.srem(PENDING_SET_KEY, str(job["inquiry_id"]))
        record_inquiry_job_operation(
            "complete",
            job.get("job_type", "scheduled_rerun"),
            status="failed",
        )
        await self._refresh_depth()

    async def stats(self) -> dict[str, Any]:
        queued, pending = await self._redis.pipeline().llen(QUEUE_LIST_KEY).scard(PENDING_SET_KEY).execute()
        return {
            "backend": "redis",
            "queued": int(queued or 0),
            "pending": int(pending or 0),
        }

    async def _refresh_depth(self) -> None:
        stats = await self.stats()
        set_inquiry_job_queue_depth(stats["queued"], stats["pending"])


_queue_singleton: InquiryJobQueueBackend | None = None
_queue_resolved_backend: str | None = None


def resolve_inquiry_job_queue_backend() -> str:
    raw = (settings.INQUIRY_JOB_QUEUE_BACKEND or "auto").strip().lower()
    if raw == "auto":
        return "redis" if settings.REDIS_URL else "memory"
    return raw


def is_inquiry_job_queue_enabled() -> bool:
    backend = resolve_inquiry_job_queue_backend()
    return backend not in ("inline", "disabled", "off", "none")


def reset_inquiry_job_queue_singleton() -> None:
    """Test helper — clears cached queue backend."""
    global _queue_singleton, _queue_resolved_backend
    _queue_singleton = None
    _queue_resolved_backend = None


def get_inquiry_job_queue() -> InquiryJobQueueBackend | None:
    global _queue_singleton, _queue_resolved_backend

    backend = resolve_inquiry_job_queue_backend()
    if not is_inquiry_job_queue_enabled():
        return None

    if _queue_singleton is not None and _queue_resolved_backend == backend:
        return _queue_singleton

    if backend == "redis" and settings.REDIS_URL:
        try:
            _queue_singleton = RedisInquiryJobQueue(settings.REDIS_URL)
            _queue_resolved_backend = "redis"
            logger.info("Inquiry job queue: Redis")
            return _queue_singleton
        except Exception as exc:
            logger.warning("Redis inquiry job queue unavailable, using memory: %s", exc)

    _queue_singleton = MemoryInquiryJobQueue()
    _queue_resolved_backend = "memory"
    logger.info("Inquiry job queue: memory")
    return _queue_singleton


async def get_inquiry_job_queue_stats() -> dict[str, Any]:
    queue = get_inquiry_job_queue()
    if queue is None:
        return {
            "enabled": False,
            "backend": resolve_inquiry_job_queue_backend(),
            "queued": 0,
            "pending": 0,
        }
    stats = await queue.stats()
    return {
        "enabled": True,
        "worker_mode": settings.INQUIRY_WORKER_MODE,
        **stats,
    }
