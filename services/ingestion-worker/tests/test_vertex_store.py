"""
VertexVectorSearchStore logic, proven with fakes (no GCP/aiplatform needed).

Validates: upsert writes payloads to the doc store + datapoints (with restricts)
to the index; query resolves neighbor IDs back to Chunks in order with the right
score; metadata filters become restricts; missing docs are skipped; and the
abstract retrieve() (hybrid keyword boost) works unchanged on the Vertex store.
"""
from dataclasses import dataclass

import pytest

from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.retrieval import retrieve
from ingestion_worker.types import Chunk
from ingestion_worker.vertex_store import (
    InMemoryDocStore,
    VertexVectorSearchStore,
    distance_to_score,
)


@dataclass
class FakeNeighbor:
    id: str
    distance: float


class FakeEndpoint:
    def __init__(self, neighbors):
        self.neighbors = neighbors
        self.calls = []

    def find_neighbors(self, *, deployed_index_id, queries, num_neighbors, filter):
        self.calls.append(
            {"deployed_index_id": deployed_index_id, "queries": queries,
             "num_neighbors": num_neighbors, "filter": filter}
        )
        return [self.neighbors[:num_neighbors]]


class FakeIndex:
    def __init__(self):
        self.upserts = []

    def upsert_datapoints(self, *, datapoints):
        self.upserts.append(datapoints)


def _fake_namespace(ns, allow):
    return {"namespace": ns, "allow": allow}


def _chunk(i, section, text=None):
    return Chunk(
        doc_id="H0567500", brand="Jandy", model="AquaPure", section=section,
        url="https://example/u", text=text or f"[{section}] body {i}",
        chunk_index=i, vector=[0.1, 0.2, 0.3, 0.4],
    )


def _store(neighbors):
    ep, idx, docs = FakeEndpoint(neighbors), FakeIndex(), InMemoryDocStore()
    store = VertexVectorSearchStore(
        endpoint=ep, index=idx, docs=docs, deployed_index_id="dep-1",
        distance_measure="COSINE_DISTANCE", namespace_factory=_fake_namespace,
    )
    return store, docs, idx, ep


def test_distance_to_score():
    assert distance_to_score(0.1, "COSINE_DISTANCE") == pytest.approx(0.9)
    assert distance_to_score(5.0, "DOT_PRODUCT_DISTANCE") == 5.0
    assert distance_to_score(2.0, "SQUARED_L2_DISTANCE") == -2.0


def test_upsert_writes_docs_and_datapoints_with_restricts():
    store, docs, idx, _ = _store([])
    c1, c2 = _chunk(0, "Service Code 125"), _chunk(1, "Operation")
    assert store.upsert([c1, c2]) == 2
    assert docs.count() == 2
    assert len(idx.upserts) == 1
    dps = idx.upserts[0]
    assert {d["datapoint_id"] for d in dps} == {c1.chunk_id, c2.chunk_id}
    assert dps[0]["feature_vector"] == [0.1, 0.2, 0.3, 0.4]
    namespaces = {r["namespace"] for r in dps[0]["restricts"]}
    assert namespaces == {"brand", "model"}


def test_query_resolves_ids_in_order_with_scores_and_filters():
    c1, c2 = _chunk(0, "Service Code 125"), _chunk(1, "Operation")
    neighbors = [FakeNeighbor(c1.chunk_id, 0.1), FakeNeighbor(c2.chunk_id, 0.4)]
    store, _docs, _idx, ep = _store(neighbors)
    store.upsert([c1, c2])

    res = store.query([0.1, 0.2, 0.3, 0.4], top_k=2, filters={"brand": "Jandy"})
    assert [c.chunk_id for c, _ in res] == [c1.chunk_id, c2.chunk_id]
    assert res[0][1] == pytest.approx(0.9)  # 1 - 0.1
    assert res[1][1] == pytest.approx(0.6)  # 1 - 0.4
    assert ep.calls[0]["num_neighbors"] == 2
    assert ep.calls[0]["filter"] == [{"namespace": "brand", "allow": ["Jandy"]}]


def test_query_skips_missing_docs_and_no_filter():
    c1 = _chunk(0, "X")
    neighbors = [FakeNeighbor(c1.chunk_id, 0.1), FakeNeighbor("missing:99", 0.2)]
    store, _docs, _idx, ep = _store(neighbors)
    store.upsert([c1])
    res = store.query([0.1, 0.2, 0.3, 0.4], top_k=5)
    assert [c.chunk_id for c, _ in res] == [c1.chunk_id]
    assert ep.calls[0]["filter"] is None


def test_retrieve_keyword_boost_works_on_vertex_store():
    """Exact fault-code keyword boost must lift the 125 chunk above a
    denser-but-wrong neighbor — proving retrieval is store-agnostic."""
    c_oper = _chunk(0, "Operation", text="[Operation] display shows readings")
    c_125 = _chunk(1, "Service Code 125", text="[Service Code 125] no flow detected 125")
    # Endpoint ranks Operation first (lower distance); keyword boost must override.
    neighbors = [FakeNeighbor(c_oper.chunk_id, 0.1), FakeNeighbor(c_125.chunk_id, 0.2)]
    store, _docs, _idx, _ep = _store(neighbors)
    store.upsert([c_oper, c_125])

    res = retrieve(store, FakeEmbedder(), "what is code 125", top_k=2)
    assert "125" in res[0].chunk.section
