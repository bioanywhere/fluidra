"""
Offline RAG fixture: ingest the bundled manual into an in-memory store with fake
embeddings and provide a fake LLM. No Docker, no Vertex.
"""
from pathlib import Path

import pytest

from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.pipeline import ingest
from ingestion_worker.vectorstore import InMemoryVectorStore

from orchestrator.llm import FakeLLM

MANUAL = Path(__file__).resolve().parents[3] / "data" / "manuals" / "aquapure_h0567500.md"


@pytest.fixture
def rag():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    ingest(
        str(MANUAL),
        doc_id="H0567500", brand="Jandy", model="AquaPure",
        url="https://www.jandy.com/en/products/sanitizers/aquapure",
        embedder=embedder, store=store,
    )
    return store, embedder, FakeLLM()
