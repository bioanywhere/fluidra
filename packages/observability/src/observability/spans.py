"""
Span helpers — a thin, dependency-light way to create spans and attach typed
attributes (tier, intent, tokens, cost, groundedness; blueprint §9.2).
"""
from __future__ import annotations

from contextlib import contextmanager

from .otel import get_tracer

_PRIMITIVES = (str, bool, int, float)


def _coerce(value):
    if value is None:
        return None
    if isinstance(value, _PRIMITIVES):
        return value
    return str(value)


def set_attributes(span, **attrs) -> None:
    """Set span attributes, skipping None and coercing non-primitives to str."""
    for key, value in attrs.items():
        coerced = _coerce(value)
        if coerced is not None:
            span.set_attribute(key, coerced)


@contextmanager
def span(name: str, **attrs):
    """Start a current span with optional initial attributes."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as current:
        set_attributes(current, **attrs)
        yield current
