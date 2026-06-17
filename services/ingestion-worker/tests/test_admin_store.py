"""list_documents / delete_document on the vector store (corpus admin, §8)."""
from pathlib import Path

from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.pipeline import ingest
from ingestion_worker.vectorstore import InMemoryVectorStore

MANUALS = Path(__file__).resolve().parents[3] / "data" / "manuals"


def _store_with(*docs):
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    for path, doc_id, brand, model in docs:
        ingest(
            str(MANUALS / path), doc_id=doc_id, brand=brand, model=model,
            url="", embedder=embedder, store=store,
        )
    return store


def test_list_documents_groups_by_doc():
    store = _store_with(
        ("aquapure_h0567500.md", "H0567500", "Jandy", "AquaPure"),
        ("jandy_jxi_heater.md", "H0608600", "Jandy", "JXi"),
    )
    docs = {d["doc_id"]: d for d in store.list_documents()}
    assert set(docs) == {"H0567500", "H0608600"}
    assert docs["H0567500"]["brand"] == "Jandy"
    assert docs["H0567500"]["chunks"] > 0
    assert sum(d["chunks"] for d in docs.values()) == store.count()


def test_delete_document_removes_only_that_doc():
    store = _store_with(
        ("aquapure_h0567500.md", "H0567500", "Jandy", "AquaPure"),
        ("jandy_jxi_heater.md", "H0608600", "Jandy", "JXi"),
    )
    before = store.count()
    removed = store.delete_document("H0567500")
    assert removed > 0
    assert store.count() == before - removed
    assert {d["doc_id"] for d in store.list_documents()} == {"H0608600"}


def test_delete_missing_document_is_zero():
    store = _store_with(("aquapure_h0567500.md", "H0567500", "Jandy", "AquaPure"))
    assert store.delete_document("NOPE") == 0


def test_reingest_same_doc_id_does_not_duplicate():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    args = dict(doc_id="H0567500", brand="Jandy", model="AquaPure", url="", embedder=embedder, store=store)
    ingest(str(MANUALS / "aquapure_h0567500.md"), **args)
    first = store.count()
    ingest(str(MANUALS / "aquapure_h0567500.md"), **args)  # upsert, same chunk_ids
    assert store.count() == first
