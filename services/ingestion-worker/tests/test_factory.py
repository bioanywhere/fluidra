"""The vector-store factory selects the backend by arg/env (config-only swap)."""
import pytest

from ingestion_worker.vectorstore import get_vector_store, InMemoryVectorStore


def test_factory_inmemory():
    assert isinstance(get_vector_store(8, backend="inmemory"), InMemoryVectorStore)


def test_factory_reads_env(monkeypatch):
    monkeypatch.setenv("VECTOR_BACKEND", "inmemory")
    assert isinstance(get_vector_store(8), InMemoryVectorStore)


def test_factory_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_vector_store(8, backend="nope")
