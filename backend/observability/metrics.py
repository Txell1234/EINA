"""Prometheus metrics for the Q2FS pipeline."""
from __future__ import annotations

import os

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

try:
    from prometheus_client import REGISTRY
    from prometheus_client.multiprocess import MultiProcessCollector

    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        MultiProcessCollector(REGISTRY)
except Exception:  # pragma: no cover
    pass

INQUIRY_REQUESTS_TOTAL = Counter(
    "q2fs_inquiry_requests_total",
    "Total Q2FS inquiry HTTP requests",
    ["mode", "status"],
)

INQUIRY_DURATION_SECONDS = Histogram(
    "q2fs_inquiry_duration_seconds",
    "Q2FS inquiry HTTP request duration",
    ["mode"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300],
)

LLM_PARSE_DURATION_SECONDS = Histogram(
    "q2fs_llm_parse_duration_seconds",
    "Parse trigger latency",
    ["llm_used"],
    buckets=[0.1, 0.25, 0.5, 1, 2, 5, 8, 15],
)

LLM_PARSE_CONFIDENCE = Gauge(
    "q2fs_llm_parse_confidence",
    "Latest parse trigger confidence (0-1)",
)

LLM_PARSE_LOW_CONFIDENCE_TOTAL = Counter(
    "q2fs_llm_parse_low_confidence_total",
    "Parse triggers with confidence below threshold",
)

LLM_TOKENS_USED_TOTAL = Counter(
    "q2fs_llm_tokens_used_total",
    "LLM tokens consumed",
    ["operation"],
)

CCA_COMBINATIONS_TOTAL = Counter(
    "q2fs_cca_combinations_total",
    "Morph combinations before CCA pruning",
)

CCA_PRUNED_TOTAL = Counter(
    "q2fs_cca_pruned_total",
    "Morph combinations pruned by CCA",
)

MORPH_VALID_CONFIGS = Gauge(
    "q2fs_morph_valid_configs",
    "Valid morph configurations after CCA",
)

CACHE_HIT_RATE = Gauge(
    "q2fs_cache_hit_rate",
    "Step cache hit rate (last observed step)",
)

CACHE_OPERATIONS_TOTAL = Counter(
    "q2fs_cache_operations_total",
    "Step cache operations",
    ["operation", "hit"],
)

Q2FS_ERRORS_TOTAL = Counter(
    "q2fs_errors_total",
    "Errors by Q2FS pipeline phase",
    ["phase", "error_type"],
)

FINANCIAL_CROSSOVER_DURATION_SECONDS = Histogram(
    "q2fs_financial_crossover_duration_seconds",
    "Financial crossover step latency",
    buckets=[0.5, 1, 2, 5, 10, 30, 60],
)

PARSE_FALLBACK_TOTAL = Counter(
    "q2fs_parse_fallback_total",
    "Parse trigger fallbacks to rule-based",
    ["reason"],
)


def expose_metrics_app():
    return make_asgi_app()


def record_cache_operation(*, hit: bool, operation: str = "get") -> None:
    CACHE_OPERATIONS_TOTAL.labels(operation=operation, hit="true" if hit else "false").inc()
    CACHE_HIT_RATE.set(1.0 if hit else 0.0)
