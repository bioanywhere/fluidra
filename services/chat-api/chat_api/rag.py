"""
RAG dependency: the (vector store, embedder, LLM) triple the pipeline needs.

Built lazily from env on first use so the app boots without the index/creds, and
overridable in tests via FastAPI dependency_overrides (in-memory + fake).

Env: DATABASE_URL_SYNC, EMBEDDING_BACKEND, LLM_BACKEND.
"""
from __future__ import annotations

import os

from ingestion_worker.embeddings import get_embedder
from ingestion_worker.vectorstore import PgVectorStore
from orchestrator.llm import get_llm

_rag: dict = {}


def get_rag():
    if not _rag:
        embedder = get_embedder()
        dsn = os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg2://postgres:localdev@localhost:5432/assistant",
        )
        _rag["embedder"] = embedder
        _rag["store"] = PgVectorStore(dsn=dsn, dim=embedder.dim)
        _rag["llm"] = get_llm()
    return _rag["store"], _rag["embedder"], _rag["llm"]
