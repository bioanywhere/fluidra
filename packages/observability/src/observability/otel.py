"""
OpenTelemetry setup (blueprint §9.2) — one instrumentation, many backends.

`init_tracing(service)` is called once at service startup. The exporter is chosen
by OTEL_TRACES_EXPORTER (none | console | gcp | otlp); real exporters are
imported lazily so local/CI need no backend. With no exporter configured the
global provider stays the default no-op, so spans are essentially free.
"""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
)

TRACER_NAME = "fluidra"


def _select_exporter():
    backend = os.getenv("OTEL_TRACES_EXPORTER", "none").lower()
    if backend in ("none", ""):
        return None
    if backend == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        return ConsoleSpanExporter()
    if backend in ("gcp", "cloud_trace"):
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter  # lazy

        return CloudTraceSpanExporter()
    if backend == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # lazy
            OTLPSpanExporter,
        )

        return OTLPSpanExporter()
    return None


def init_tracing(service_name: str, exporter=None, *, simple: bool = False):
    """Configure the global tracer provider. No-op (default provider) when no
    exporter is configured. Returns a tracer for the service."""
    exp = exporter or _select_exporter()
    if exp is None:
        return get_tracer(service_name)

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    use_simple = simple or exporter is not None  # deterministic for tests
    provider.add_span_processor(
        SimpleSpanProcessor(exp) if use_simple else BatchSpanProcessor(exp)
    )
    trace.set_tracer_provider(provider)
    return get_tracer(service_name)


def get_tracer(name: str = TRACER_NAME):
    return trace.get_tracer(name)


def configure_in_memory():
    """Test helper: attach an in-memory exporter to (an ensured real) provider
    and return it, so tests can assert on captured spans without a backend."""
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter
