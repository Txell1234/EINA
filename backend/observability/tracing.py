"""OpenTelemetry tracing (Jaeger via OTLP)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import settings

_tracer = None
_initialized = False


def setup_jaeger_tracing(app=None) -> bool:
    global _tracer, _initialized
    if _initialized:
        return _tracer is not None
    if not settings.OTEL_ENABLED:
        _initialized = True
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    except ImportError:  # pragma: no cover
        _initialized = True
        return False

    endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
    service_name = settings.OTEL_SERVICE_NAME
    sampler_rate = max(0.0, min(1.0, settings.OTEL_TRACES_SAMPLER_RATE))

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sampler_rate),
    )
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("eina.q2fs")

    if app is not None:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=provider,
            excluded_urls="metrics,health,docs,redoc,openapi.json",
        )

    _initialized = True
    return True


def get_tracer():
    if _tracer is None and not _initialized:
        setup_jaeger_tracing()
    return _tracer


@contextmanager
def q2fs_span(name: str, phase: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry import trace as otel_trace

    with tracer.start_as_current_span(name) as span:
        span.set_attribute("q2fs.phase", phase)
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_status(otel_trace.Status(otel_trace.StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
