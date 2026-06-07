"""Tests for inquiry job queue."""
from __future__ import annotations

import pytest

from observability.inquiry_job_queue import MemoryInquiryJobQueue


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_queue_enqueue_dequeue_complete():
    queue = MemoryInquiryJobQueue()
    assert await queue.enqueue(42, "scheduled_rerun") is True
    stats = await queue.stats()
    assert stats["queued"] == 1
    assert stats["pending"] == 1

    job = await queue.dequeue()
    assert job is not None
    assert job["inquiry_id"] == 42
    assert job["job_type"] == "scheduled_rerun"
    assert job["force_refresh"] is True

    stats = await queue.stats()
    assert stats["queued"] == 0
    assert stats["pending"] == 1

    await queue.complete(job)
    stats = await queue.stats()
    assert stats["pending"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_queue_dedupes_pending_inquiry():
    queue = MemoryInquiryJobQueue()
    assert await queue.enqueue(7, "scheduled_rerun") is True
    assert await queue.enqueue(7, "scheduled_rerun") is False

    stats = await queue.stats()
    assert stats["queued"] == 1
    assert stats["pending"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_queue_fail_clears_pending():
    queue = MemoryInquiryJobQueue()
    await queue.enqueue(99, "manual_rerun", force_refresh=False)
    job = await queue.dequeue()
    assert job is not None
    await queue.fail(job, "boom")

    stats = await queue.stats()
    assert stats["pending"] == 0
    assert stats["queued"] == 0

    assert await queue.enqueue(99, "manual_rerun") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_queue_fifo_order():
    queue = MemoryInquiryJobQueue()
    await queue.enqueue(1, "scheduled_rerun")
    await queue.enqueue(2, "scheduled_rerun")
    first = await queue.dequeue()
    second = await queue.dequeue()
    assert first is not None and first["inquiry_id"] == 1
    assert second is not None and second["inquiry_id"] == 2
