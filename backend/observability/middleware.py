"""FastAPI middleware for Prometheus and trace correlation headers."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from observability.correlation import get_correlation_ids, sync_trace_context_from_otel
from observability.metrics import INQUIRY_DURATION_SECONDS, INQUIRY_REQUESTS_TOTAL, Q2FS_ERRORS_TOTAL


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        is_q2fs = "/inquiries" in path or "/prospective" in path
        start = time.perf_counter()
        mode = request.query_params.get("mode", "full")

        try:
            response = await call_next(request)
            if is_q2fs:
                duration = time.perf_counter() - start
                status = "success" if response.status_code < 400 else "failed"
                INQUIRY_REQUESTS_TOTAL.labels(mode=mode, status=status).inc()
                INQUIRY_DURATION_SECONDS.labels(mode=mode).observe(duration)

            ids = sync_trace_context_from_otel()
            if ids.get("trace_id"):
                response.headers["X-Trace-Id"] = ids["trace_id"]  # type: ignore[arg-type]
            if ids.get("span_id"):
                response.headers["X-Span-Id"] = ids["span_id"]  # type: ignore[arg-type]
            return response
        except Exception as exc:
            if is_q2fs:
                Q2FS_ERRORS_TOTAL.labels(phase="middleware", error_type=type(exc).__name__).inc()
            raise


class CorrelationLoggingMiddleware(BaseHTTPMiddleware):
    """Ensure trace IDs are available early in the request lifecycle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        get_correlation_ids()
        return await call_next(request)
