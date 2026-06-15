"""
Full-corpus ingestion + cross-manual retrieval (offline).

Proves the manifest ingests every manual and that a fault-code query returns the
RIGHT manual's section — not a similar-looking section from another brand/model.
"""
import pytest

from ingestion_worker.corpus import ingest_corpus, load_manifest
from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.retrieval import retrieve
from ingestion_worker.vectorstore import InMemoryVectorStore


@pytest.fixture
def corpus():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    results = ingest_corpus(store, embedder)
    return store, embedder, results


def test_manifest_lists_multiple_manuals():
    specs = load_manifest()
    doc_ids = {s.doc_id for s in specs}
    assert {"H0567500", "POL-ALPHAIQ", "H0608600", "H0574100"} <= doc_ids


def test_all_manuals_ingested(corpus):
    store, _embedder, results = corpus
    assert len(results) == 4
    assert all(r.chunks > 0 for r in results.values())
    assert store.count() == sum(r.chunks for r in results.values())


@pytest.mark.parametrize(
    "query,expected_doc,expected_code",
    [
        ("my salt system shows code 125", "H0567500", "125"),
        ("what does polaris error 215 mean", "POL-ALPHAIQ", "215"),
        ("jandy jxi heater fault 301", "H0608600", "301"),
        ("vs flopro pump fault 410", "H0574100", "410"),
    ],
)
def test_fault_code_returns_correct_manual(corpus, query, expected_doc, expected_code):
    store, embedder, _ = corpus
    results = retrieve(store, embedder, query, top_k=6)
    top = results[0]
    assert top.chunk.doc_id == expected_doc, f"{query!r} -> {top.chunk.doc_id}"
    assert expected_code in top.chunk.section


def test_brand_prefilter_scopes_results(corpus):
    store, embedder, _ = corpus
    results = retrieve(store, embedder, "error 215", top_k=6, filters={"brand": "Polaris"})
    assert results
    assert all(s.chunk.brand == "Polaris" for s in results)
