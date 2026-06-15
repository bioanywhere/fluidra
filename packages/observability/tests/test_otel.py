"""Spans are created with typed attributes and nest correctly (offline)."""
from observability import configure_in_memory, init_tracing, set_attributes, span


def test_span_records_attributes():
    exporter = configure_in_memory()
    with span("unit.turn", **{"safety.tier": "T1"}) as s:
        set_attributes(s, **{"ai.groundedness": 0.95, "skip.me": None})
    finished = {sp.name: sp for sp in exporter.get_finished_spans()}
    assert "unit.turn" in finished
    attrs = finished["unit.turn"].attributes
    assert attrs["safety.tier"] == "T1"
    assert attrs["ai.groundedness"] == 0.95
    assert "skip.me" not in attrs  # None is skipped


def test_spans_nest():
    exporter = configure_in_memory()
    with span("parent"):
        with span("child"):
            pass
    names = [sp.name for sp in exporter.get_finished_spans()]
    assert "parent" in names and "child" in names


def test_init_tracing_without_backend_is_noop():
    # OTEL_TRACES_EXPORTER unset -> returns a tracer, does not raise
    assert init_tracing("svc") is not None
