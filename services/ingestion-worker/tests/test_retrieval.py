"""
End-to-end retrieval test (offline): ingest the bundled manual into the
in-memory store with fake embeddings, then prove a known fault-code query
returns the correct manual section as the top hit.
"""
from pathlib import Path

import pytest

from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.pipeline import ingest
from ingestion_worker.retrieval import retrieve
from ingestion_worker.vectorstore import InMemoryVectorStore

MANUAL = Path(__file__).resolve().parents[3] / "data" / "manuals" / "aquapure_h0567500.md"


@pytest.fixture
def store_and_embedder():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    result = ingest(
        str(MANUAL),
        doc_id="H0567500", brand="Jandy", model="AquaPure",
        url="https://www.jandy.com/en/products/sanitizers/aquapure",
        embedder=embedder, store=store,
    )
    assert result.indexed == store.count() > 0
    return store, embedder


def test_fault_code_125_returns_correct_section(store_and_embedder):
    store, embedder = store_and_embedder
    results = retrieve(store, embedder, "my salt system shows code 125", top_k=6)
    assert results, "no results returned"
    top = results[0]
    assert "125" in top.chunk.section, f"top hit was {top.chunk.section!r}"
    assert top.keyword > 0, "exact code 125 should contribute a keyword boost"
    assert "flow" in top.chunk.text.lower()


def test_retrieval_returns_at_most_top_k(store_and_embedder):
    store, embedder = store_and_embedder
    results = retrieve(store, embedder, "salt chlorine generator", top_k=6)
    assert 0 < len(results) <= 6


def test_keyword_boost_disambiguates_similar_codes(store_and_embedder):
    """Code 124 (High Salt) and 125 (No Flow) are textually similar; the keyword
    boost must put the exact code on top."""
    store, embedder = store_and_embedder
    r125 = retrieve(store, embedder, "what is service code 125", top_k=3)
    r124 = retrieve(store, embedder, "what is service code 124", top_k=3)
    assert "125" in r125[0].chunk.section
    assert "124" in r124[0].chunk.section


def test_metadata_prefilter(store_and_embedder):
    store, embedder = store_and_embedder
    # Matching brand returns hits; a non-present brand returns nothing.
    hit = retrieve(store, embedder, "code 125", filters={"brand": "Jandy"})
    miss = retrieve(store, embedder, "code 125", filters={"brand": "Pentair"})
    assert hit and "125" in hit[0].chunk.section
    assert miss == []
