"""Correlate OpenTelemetry traces with Prometheus metrics and structured logs."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_trace_id: ContextVar[str | None] = ContextVar("q2fs_trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("q2fs_span_id", default=None)

try:
    from opentelemetry import trace as otel_trace
except ImportError:  # pragma: no cover
    otel_trace = None  # type: ignore[assignment]


def _format_trace_id(raw: int) -> str:
    return f"{raw:032x}"


def _format_span_id(raw: int) -> str:
    return f"{raw:016x}"


def sync_trace_context_from_otel() -> dict[str, str | None]:
    """Read active span IDs into context vars for logging."""
    if otel_trace is None:
        return {"trace_id": None, "span_id": None}

    span = otel_trace.get_current_span()
    ctx = span.get_span_context() if span else None
    if not ctx or not ctx.is_valid:
        return {"trace_id": _trace_id.get(), "span_id": _span_id.get()}

    trace_id = _format_trace_id(ctx.trace_id)
    span_id = _format_span_id(ctx.span_id)
    _trace_id.set(trace_id)
    _span_id.set(span_id)
    return {"trace_id": trace_id, "span_id": span_id}


def get_correlation_ids() -> dict[str, str | None]:
    sync_trace_context_from_otel()
    return {
        "trace_id": _trace_id.get(),
        "span_id": _span_id.get(),
    }


def correlation_log_extra(**extra: Any) -> dict[str, Any]:
    ids = get_correlation_ids()
    out = {k: v for k, v in ids.items() if v}
    out.update(extra)
    return out
