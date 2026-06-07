"""Tests for Q2FS observability helpers."""
from __future__ import annotations

import pytest

from observability.correlation import correlation_log_extra, get_correlation_ids
from observability.metrics import record_cache_operation, record_inquiry_job_operation
from observability.step_cache import MemoryStepCache, StepCacheBackend


@pytest.mark.unit
def test_correlation_ids_default():
    ids = get_correlation_ids()
    assert "trace_id" in ids
    assert "span_id" in ids


@pytest.mark.unit
def test_correlation_log_extra():
    extra = correlation_log_extra(phase="parse_trigger", inquiry_id=1)
    assert extra["phase"] == "parse_trigger"
    assert extra["inquiry_id"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_step_cache():
    cache = MemoryStepCache()
    assert await cache.get(1, "osint") is None
    await cache.set(1, "osint", {"hits": 3})
    hit = await cache.get(1, "osint")
    assert hit == {"hits": 3}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_memory_step_cache_semantic():
    cache = MemoryStepCache()
    await cache.set_semantic("Hormuz blockade lifted?", "osint", {"kept": 5})
    hit = await cache.get_semantic("hormuz blockade lifted?", "osint")
    assert hit == {"kept": 5}


@pytest.mark.unit
def test_semantic_key_stable():
    k1 = StepCacheBackend.semantic_key("Trump  Hormuz   lifted?")
    k2 = StepCacheBackend.semantic_key("trump hormuz lifted?")
    assert k1 == k2


@pytest.mark.unit
def test_record_cache_operation_no_crash():
    record_cache_operation(hit=True)
    record_cache_operation(hit=False, operation="set")


@pytest.mark.unit
def test_record_inquiry_job_operation_no_crash():
    record_inquiry_job_operation("enqueue", "scheduled_rerun", status="ok")
    record_inquiry_job_operation("complete", "manual_rerun", status="failed")
