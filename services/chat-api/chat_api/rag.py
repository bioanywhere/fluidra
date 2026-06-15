"""
RAG dependency: the (vector store, embedder, LLM) triple the pipeline needs.

Built lazily from env on first use so the app boots without the index/creds, and
overridable in tests via FastAPI dependency_overrides (in-memory + fake).

Env: VECTOR_BACKEND, DATABASE_URL_SYNC, EMBEDDING_BACKEND, LLM_BACKEND.
"""
from __future__ import annotations

from ingestion_worker.embeddings import get_embedder
from ingestion_worker.vectorstore import get_vector_store
from orchestrator.llm import get_llm

_rag: dict = {}


def get_rag():
    if not _rag:
        embedder = get_embedder()
        _rag["embedder"] = embedder
        # Backend chosen by VECTOR_BACKEND env (pgvector | vertex | inmemory).
        _rag["store"] = get_vector_store(embedder.dim)
        _rag["llm"] = get_llm()
    return _rag["store"], _rag["embedder"], _rag["llm"]
