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

from typing import Protocol

import numpy as np

from .types import Chunk


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk]) -> int: ...
    def query(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]: ...
    def count(self) -> int: ...


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

    def count(self) -> int:
        return len(self._chunks)


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

    def count(self) -> int:
        from sqlalchemy import text

        with self._engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {self._table}")).scalar())
