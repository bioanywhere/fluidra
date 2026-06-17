"""
Vector store abstraction.

The retrieval interface is deliberately abstract (blueprint: pgvector is the
small-scale fallback; Vertex AI Vector Search swaps in later with NO call-site
changes). Two implementations ship now:

  - InMemoryVectorStore : zero-dependency, used by tests and offline dev.
  - PgVectorStore       : Postgres + pgvector, used by `make dev` / Cloud SQL.

A future VertexVectorSearchStore implements the same `VectorStore` protocol.
`query()` returns dense (cosine) candidates; keyword/hybrid re-ranking lives in
retrieval.py so it is identical across stores.
"""
from __future__ import annotations

import os
import re
from typing import Protocol

import numpy as np

from .types import Chunk


def _term_patterns(terms: list[str]) -> list[re.Pattern]:
    return [re.compile(rf"\b{re.escape(t)}\b", re.I) for t in terms]


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk]) -> int: ...
    def query(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]: ...
    def count(self) -> int: ...
    # Corpus administration (blueprint §8): list distinct documents and remove one.
    def list_documents(self) -> list[dict]: ...
    def delete_document(self, doc_id: str) -> int: ...


def _matches(chunk: Chunk, filters: dict | None) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if getattr(chunk, key, None) != value:
            return False
    return True


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


class InMemoryVectorStore:
    """In-process cosine store. Each chunk must already carry `vector`."""

    def __init__(self):
        self._chunks: dict[str, Chunk] = {}

    def upsert(self, chunks: list[Chunk]) -> int:
        for c in chunks:
            if c.vector is None:
                raise ValueError(f"chunk {c.chunk_id} has no vector")
            self._chunks[c.chunk_id] = c
        return len(chunks)

    def query(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        q = np.asarray(vector, dtype=np.float64)
        scored = [
            (c, _cosine(q, np.asarray(c.vector, dtype=np.float64)))
            for c in self._chunks.values()
            if _matches(c, filters)
        ]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]

    def keyword_search(
        self, terms: list[str], limit: int, filters: dict | None = None
    ) -> list[Chunk]:
        """Chunks containing any term as a whole token (word-boundary match)."""
        if not terms:
            return []
        pats = _term_patterns(terms)
        out: list[Chunk] = []
        for c in self._chunks.values():
            if not _matches(c, filters):
                continue
            if any(p.search(c.text) for p in pats):
                out.append(c)
            if len(out) >= limit:
                break
        return out

    def count(self) -> int:
        return len(self._chunks)

    def list_documents(self) -> list[dict]:
        docs: dict[str, dict] = {}
        for c in self._chunks.values():
            d = docs.setdefault(
                c.doc_id,
                {"doc_id": c.doc_id, "brand": c.brand, "model": c.model,
                 "url": c.url, "locale": c.locale, "chunks": 0},
            )
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["doc_id"])

    def delete_document(self, doc_id: str) -> int:
        ids = [cid for cid, c in self._chunks.items() if c.doc_id == doc_id]
        for cid in ids:
            del self._chunks[cid]
        return len(ids)


class PgVectorStore:
    """Postgres + pgvector implementation. Libraries are imported lazily so the
    module loads without sqlalchemy/pgvector installed (tests use InMemory)."""

    def __init__(self, dsn: str, dim: int, table: str = "manual_chunks"):
        from sqlalchemy import create_engine
        from pgvector.sqlalchemy import Vector  # noqa: F401  (registers type)

        self._dim = dim
        self._table = table
        self._engine = create_engine(dsn)
        self._ensure_schema()

    def _ensure_schema(self):
        from sqlalchemy import text

        with self._engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._table} (
                        chunk_id    TEXT PRIMARY KEY,
                        doc_id      TEXT NOT NULL,
                        brand       TEXT,
                        model       TEXT,
                        section     TEXT,
                        url         TEXT,
                        locale      TEXT,
                        chunk_index INTEGER,
                        text        TEXT NOT NULL,
                        embedding   vector({self._dim})
                    )
                    """
                )
            )

    def upsert(self, chunks: list[Chunk]) -> int:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            for c in chunks:
                if c.vector is None:
                    raise ValueError(f"chunk {c.chunk_id} has no vector")
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {self._table}
                          (chunk_id, doc_id, brand, model, section, url, locale,
                           chunk_index, text, embedding)
                        VALUES
                          (:chunk_id, :doc_id, :brand, :model, :section, :url,
                           :locale, :chunk_index, :text, :embedding)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                          text = EXCLUDED.text, embedding = EXCLUDED.embedding
                        """
                    ),
                    {
                        "chunk_id": c.chunk_id,
                        "doc_id": c.doc_id,
                        "brand": c.brand,
                        "model": c.model,
                        "section": c.section,
                        "url": c.url,
                        "locale": c.locale,
                        "chunk_index": c.chunk_index,
                        "text": c.text,
                        "embedding": str(c.vector),
                    },
                )
        return len(chunks)

    def query(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        from sqlalchemy import text

        where = ""
        params: dict = {"q": str(vector), "k": top_k}
        if filters:
            clauses = []
            for i, (key, value) in enumerate(filters.items()):
                clauses.append(f"{key} = :f{i}")
                params[f"f{i}"] = value
            where = "WHERE " + " AND ".join(clauses)
        sql = text(
            f"""
            SELECT chunk_id, doc_id, brand, model, section, url, locale,
                   chunk_index, text, 1 - (embedding <=> :q) AS score
            FROM {self._table}
            {where}
            ORDER BY embedding <=> :q
            LIMIT :k
            """
        )
        out: list[tuple[Chunk, float]] = []
        with self._engine.connect() as conn:
            for row in conn.execute(sql, params):
                chunk = Chunk(
                    doc_id=row.doc_id, brand=row.brand, model=row.model,
                    section=row.section, url=row.url, text=row.text,
                    chunk_index=row.chunk_index, locale=row.locale,
                )
                out.append((chunk, float(row.score)))
        return out

    def keyword_search(
        self, terms: list[str], limit: int, filters: dict | None = None
    ) -> list[Chunk]:
        from sqlalchemy import text

        if not terms:
            return []
        # Postgres word-boundary regex (\m start, \M end of word).
        pattern = r"\m(" + "|".join(re.escape(t) for t in terms) + r")\M"
        where = ["text ~* :pat"]
        params: dict = {"pat": pattern, "k": limit}
        if filters:
            for i, (key, value) in enumerate(filters.items()):
                where.append(f"{key} = :f{i}")
                params[f"f{i}"] = value
        sql = text(
            f"""
            SELECT chunk_id, doc_id, brand, model, section, url, locale,
                   chunk_index, text
            FROM {self._table}
            WHERE {" AND ".join(where)}
            LIMIT :k
            """
        )
        out: list[Chunk] = []
        with self._engine.connect() as conn:
            for row in conn.execute(sql, params):
                out.append(
                    Chunk(
                        doc_id=row.doc_id, brand=row.brand, model=row.model,
                        section=row.section, url=row.url, text=row.text,
                        chunk_index=row.chunk_index, locale=row.locale,
                    )
                )
        return out

    def count(self) -> int:
        from sqlalchemy import text

        with self._engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {self._table}")).scalar())

    def list_documents(self) -> list[dict]:
        from sqlalchemy import text

        sql = text(
            f"""
            SELECT doc_id,
                   MAX(brand)  AS brand,
                   MAX(model)  AS model,
                   MAX(url)    AS url,
                   MAX(locale) AS locale,
                   COUNT(*)    AS chunks
            FROM {self._table}
            GROUP BY doc_id
            ORDER BY doc_id
            """
        )
        with self._engine.connect() as conn:
            return [
                {"doc_id": r.doc_id, "brand": r.brand, "model": r.model,
                 "url": r.url, "locale": r.locale, "chunks": int(r.chunks)}
                for r in conn.execute(sql)
            ]

    def delete_document(self, doc_id: str) -> int:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            res = conn.execute(
                text(f"DELETE FROM {self._table} WHERE doc_id = :d"), {"d": doc_id}
            )
            return int(res.rowcount or 0)


# ── Backend selection (config-only swap; blueprint: pgvector -> Vertex) ───────
DEFAULT_DSN = "postgresql+psycopg2://postgres:localdev@localhost:5432/assistant"


def get_vector_store(dim: int, *, backend: str | None = None, dsn: str | None = None) -> VectorStore:
    """Return the configured vector store. VECTOR_BACKEND = pgvector (default) |
    vertex | inmemory. Selecting Vertex AI Vector Search is a config change only —
    every call site uses the same VectorStore protocol."""
    backend = (backend or os.getenv("VECTOR_BACKEND", "pgvector")).lower()
    if backend == "inmemory":
        return InMemoryVectorStore()
    if backend == "pgvector":
        return PgVectorStore(dsn=dsn or os.getenv("DATABASE_URL_SYNC", DEFAULT_DSN), dim=dim)
    if backend == "vertex":
        from .vertex_store import VertexVectorSearchStore  # lazy: needs aiplatform

        return VertexVectorSearchStore.from_env(dim)
    raise ValueError(f"unknown VECTOR_BACKEND {backend!r} (use pgvector|vertex|inmemory)")
