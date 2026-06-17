"""
Vertex AI Vector Search implementation of the VectorStore protocol.

Vector Search returns only datapoint IDs + distances, so this store pairs the
ANN index with a "doc store" that resolves IDs back to full Chunks (text +
metadata). That's the standard production split: Vector Search for ANN, a
key-value store (Postgres here) for payloads. The store satisfies the same
`VectorStore` protocol as InMemoryVectorStore / PgVectorStore, so retrieval and
all call sites are unchanged — selection is config-only (VECTOR_BACKEND=vertex).

The aiplatform SDK is imported lazily (only in `from_env`), and the index /
endpoint / namespace-factory are injectable, so the orchestration logic is unit
-tested with fakes — no GCP needed in CI.
"""
from __future__ import annotations

import os
from typing import Protocol

from .types import Chunk


# ── Doc store (id -> Chunk payload) ──────────────────────────────────────────
class ChunkDocStore(Protocol):
    def put(self, chunks: list[Chunk]) -> None: ...
    def get(self, ids: list[str]) -> list[Chunk]: ...
    def count(self) -> int: ...
    def list_documents(self) -> list[dict]: ...
    def delete_document(self, doc_id: str) -> list[str]: ...


class InMemoryDocStore:
    def __init__(self) -> None:
        self._d: dict[str, Chunk] = {}

    def put(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._d[c.chunk_id] = c

    def get(self, ids: list[str]) -> list[Chunk]:
        return [self._d[i] for i in ids if i in self._d]

    def count(self) -> int:
        return len(self._d)

    def list_documents(self) -> list[dict]:
        docs: dict[str, dict] = {}
        for c in self._d.values():
            d = docs.setdefault(
                c.doc_id,
                {"doc_id": c.doc_id, "brand": c.brand, "model": c.model,
                 "url": c.url, "locale": c.locale, "chunks": 0},
            )
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["doc_id"])

    def delete_document(self, doc_id: str) -> list[str]:
        ids = [cid for cid, c in self._d.items() if c.doc_id == doc_id]
        for cid in ids:
            del self._d[cid]
        return ids


class PostgresDocStore:
    """Payload store in Postgres (sqlalchemy imported lazily)."""

    def __init__(self, dsn: str, table: str = "manual_chunk_docs"):
        from sqlalchemy import create_engine

        self._table = table
        self._engine = create_engine(dsn)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
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
                        text        TEXT NOT NULL
                    )
                    """
                )
            )

    def put(self, chunks: list[Chunk]) -> None:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            for c in chunks:
                conn.execute(
                    text(
                        f"""
                        INSERT INTO {self._table}
                          (chunk_id, doc_id, brand, model, section, url, locale,
                           chunk_index, text)
                        VALUES
                          (:chunk_id, :doc_id, :brand, :model, :section, :url,
                           :locale, :chunk_index, :text)
                        ON CONFLICT (chunk_id) DO UPDATE SET text = EXCLUDED.text
                        """
                    ),
                    {
                        "chunk_id": c.chunk_id, "doc_id": c.doc_id, "brand": c.brand,
                        "model": c.model, "section": c.section, "url": c.url,
                        "locale": c.locale, "chunk_index": c.chunk_index, "text": c.text,
                    },
                )

    def get(self, ids: list[str]) -> list[Chunk]:
        from sqlalchemy import text

        if not ids:
            return []
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT chunk_id, doc_id, brand, model, section, url, locale, "
                    f"chunk_index, text FROM {self._table} WHERE chunk_id = ANY(:ids)"
                ),
                {"ids": ids},
            ).mappings().all()
        return [
            Chunk(
                doc_id=r["doc_id"], brand=r["brand"], model=r["model"],
                section=r["section"], url=r["url"], text=r["text"],
                chunk_index=r["chunk_index"], locale=r["locale"],
            )
            for r in rows
        ]

    def count(self) -> int:
        from sqlalchemy import text

        with self._engine.connect() as conn:
            return int(conn.execute(text(f"SELECT COUNT(*) FROM {self._table}")).scalar())

    def list_documents(self) -> list[dict]:
        from sqlalchemy import text

        sql = text(
            f"""
            SELECT doc_id, MAX(brand) AS brand, MAX(model) AS model,
                   MAX(url) AS url, MAX(locale) AS locale, COUNT(*) AS chunks
            FROM {self._table} GROUP BY doc_id ORDER BY doc_id
            """
        )
        with self._engine.connect() as conn:
            return [
                {"doc_id": r.doc_id, "brand": r.brand, "model": r.model,
                 "url": r.url, "locale": r.locale, "chunks": int(r.chunks)}
                for r in conn.execute(sql)
            ]

    def delete_document(self, doc_id: str) -> list[str]:
        from sqlalchemy import text

        with self._engine.begin() as conn:
            ids = [
                row[0]
                for row in conn.execute(
                    text(f"SELECT chunk_id FROM {self._table} WHERE doc_id = :d"),
                    {"d": doc_id},
                )
            ]
            if ids:
                conn.execute(
                    text(f"DELETE FROM {self._table} WHERE doc_id = :d"), {"d": doc_id}
                )
            return ids


# ── Distance -> similarity (higher = better, to match retrieval's dense score) ─
def distance_to_score(distance: float, measure: str) -> float:
    if measure == "DOT_PRODUCT_DISTANCE":
        return float(distance)
    if measure == "COSINE_DISTANCE":
        return 1.0 - float(distance)
    if measure == "SQUARED_L2_DISTANCE":
        return -float(distance)
    return float(distance)


def _default_namespace(namespace: str, allow_list: list[str]):
    from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import (
        Namespace,
    )

    return Namespace(name=namespace, allow_tokens=allow_list, deny_tokens=[])


class VertexVectorSearchStore:
    """VectorStore backed by Vertex AI Vector Search + a doc store."""

    def __init__(
        self,
        *,
        endpoint,
        index,
        docs: ChunkDocStore,
        deployed_index_id: str,
        distance_measure: str = "COSINE_DISTANCE",
        namespace_factory=_default_namespace,
    ):
        self._endpoint = endpoint
        self._index = index
        self._docs = docs
        self._deployed_index_id = deployed_index_id
        self._measure = distance_measure
        self._namespace = namespace_factory

    @classmethod
    def from_env(cls, dim: int) -> "VertexVectorSearchStore":
        import google.cloud.aiplatform as aiplatform

        aiplatform.init(
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("VERTEX_LOCATION", "europe-west1"),
        )
        index = aiplatform.MatchingEngineIndex(os.environ["VECTOR_INDEX"])
        endpoint = aiplatform.MatchingEngineIndexEndpoint(os.environ["VECTOR_INDEX_ENDPOINT"])
        dsn = os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg2://postgres:localdev@localhost:5432/assistant",
        )
        return cls(
            endpoint=endpoint,
            index=index,
            docs=PostgresDocStore(dsn=dsn),
            deployed_index_id=os.environ["VECTOR_DEPLOYED_INDEX_ID"],
            distance_measure=os.getenv("VECTOR_DISTANCE_MEASURE", "COSINE_DISTANCE"),
        )

    def _restricts(self, filters: dict | None):
        if not filters:
            return None
        return [self._namespace(k, [v]) for k, v in filters.items()]

    def upsert(self, chunks: list[Chunk]) -> int:
        self._docs.put(chunks)
        datapoints = []
        for c in chunks:
            if c.vector is None:
                raise ValueError(f"chunk {c.chunk_id} has no vector")
            datapoints.append(
                {
                    "datapoint_id": c.chunk_id,
                    "feature_vector": list(c.vector),
                    "restricts": [
                        {"namespace": "brand", "allow_list": [c.brand]},
                        {"namespace": "model", "allow_list": [c.model]},
                    ],
                }
            )
        self._index.upsert_datapoints(datapoints=datapoints)
        return len(chunks)

    def query(
        self, vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[tuple[Chunk, float]]:
        response = self._endpoint.find_neighbors(
            deployed_index_id=self._deployed_index_id,
            queries=[vector],
            num_neighbors=top_k,
            filter=self._restricts(filters),
        )
        neighbors = response[0] if response else []
        by_id = {c.chunk_id: c for c in self._docs.get([n.id for n in neighbors])}
        out: list[tuple[Chunk, float]] = []
        for n in neighbors:
            chunk = by_id.get(n.id)
            if chunk is not None:
                out.append((chunk, distance_to_score(n.distance, self._measure)))
        return out

    def count(self) -> int:
        return self._docs.count()

    def list_documents(self) -> list[dict]:
        return self._docs.list_documents()

    def delete_document(self, doc_id: str) -> int:
        ids = self._docs.delete_document(doc_id)
        if ids:
            self._index.remove_datapoints(datapoint_ids=ids)
        return len(ids)
