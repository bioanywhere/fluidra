"""observability — shared OpenTelemetry tracing, structured logging, trace helpers."""
from .logging import get_logger, setup_logging
from .otel import configure_in_memory, get_tracer, init_tracing
from .spans import set_attributes, span
from . import langfuse_trace

VERSION = "0.1.0"

__all__ = [
    "VERSION",
    "init_tracing",
    "get_tracer",
    "configure_in_memory",
    "span",
    "set_attributes",
    "setup_logging",
    "get_logger",
    "langfuse_trace",
]
