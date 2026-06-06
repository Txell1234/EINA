"""Pluggable step cache for Q2FS orchestrator (memory or Redis)."""
from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from app.config import settings
from observability.metrics import record_cache_operation

logger = logging.getLogger(__name__)


class StepCacheBackend(ABC):
    @abstractmethod
    async def get(self, inquiry_id: int, step: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def set(self, inquiry_id: int, step: str, payload: dict[str, Any], *, ttl: int = 86400) -> None:
        ...

    @staticmethod
    def semantic_key(question: str) -> str:
        normalized = " ".join((question or "").lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class MemoryStepCache(StepCacheBackend):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._semantic: dict[str, dict[str, Any]] = {}

    def _key(self, inquiry_id: int, step: str) -> str:
        return f"{inquiry_id}:{step}"

    def _semantic_key(self, question: str, step: str) -> str:
        return f"semantic:{step}:{self.semantic_key(question)}"

    async def get(self, inquiry_id: int, step: str) -> dict[str, Any] | None:
        hit = self._store.get(self._key(inquiry_id, step))
        record_cache_operation(hit=hit is not None)
        return hit

    async def set(self, inquiry_id: int, step: str, payload: dict[str, Any], *, ttl: int = 86400) -> None:
        _ = ttl
        self._store[self._key(inquiry_id, step)] = payload
        record_cache_operation(hit=False, operation="set")

    async def get_semantic(self, question: str, step: str) -> dict[str, Any] | None:
        hit = self._semantic.get(self._semantic_key(question, step))
        record_cache_operation(hit=hit is not None, operation="semantic_get")
        return hit

    async def set_semantic(self, question: str, step: str, payload: dict[str, Any], *, ttl: int = 604800) -> None:
        _ = ttl
        self._semantic[self._semantic_key(question, step)] = payload
        record_cache_operation(hit=False, operation="semantic_set")


class RedisStepCache(StepCacheBackend):
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, decode_responses=True)

    def _key(self, inquiry_id: int, step: str) -> str:
        return f"q2fs:inquiry:{inquiry_id}:step:{step}"

    def _semantic_key(self, question: str, step: str) -> str:
        return f"q2fs:semantic:{step}:{self.semantic_key(question)}"

    async def get(self, inquiry_id: int, step: str) -> dict[str, Any] | None:
        raw = await self._redis.get(self._key(inquiry_id, step))
        hit = raw is not None
        record_cache_operation(hit=hit)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, inquiry_id: int, step: str, payload: dict[str, Any], *, ttl: int = 86400) -> None:
        body = json.dumps(payload, ensure_ascii=False)
        await self._redis.set(self._key(inquiry_id, step), body, ex=ttl)
        record_cache_operation(hit=False, operation="set")

    async def get_semantic(self, question: str, step: str) -> dict[str, Any] | None:
        raw = await self._redis.get(self._semantic_key(question, step))
        record_cache_operation(hit=raw is not None, operation="semantic_get")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_semantic(self, question: str, step: str, payload: dict[str, Any], *, ttl: int = 604800) -> None:
        body = json.dumps(payload, ensure_ascii=False)
        await self._redis.set(self._semantic_key(question, step), body, ex=ttl)
        record_cache_operation(hit=False, operation="semantic_set")


_cache_singleton: StepCacheBackend | None = None


def get_step_cache() -> StepCacheBackend | None:
    global _cache_singleton
    if _cache_singleton is not None:
        return _cache_singleton

    backend = (settings.Q2FS_STEP_CACHE_BACKEND or "memory").strip().lower()
    if backend == "redis" and settings.REDIS_URL:
        try:
            _cache_singleton = RedisStepCache(settings.REDIS_URL)
            logger.info("Q2FS step cache: Redis")
            return _cache_singleton
        except Exception as exc:
            logger.warning("Redis step cache unavailable, using memory: %s", exc)

    if backend == "redis":
        _cache_singleton = MemoryStepCache()
        logger.info("Q2FS step cache: memory (Redis URL missing)")
        return _cache_singleton

    if backend == "memory":
        _cache_singleton = MemoryStepCache()
        logger.info("Q2FS step cache: memory")
        return _cache_singleton

    return None
