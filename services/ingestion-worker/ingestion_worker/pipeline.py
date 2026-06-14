"""
Ingestion pipeline (blueprint §8.1, MVP slice).

  parse -> structure-aware chunk (+metadata) -> embed -> upsert into vector store

The validation gate / canary-eval / index-promotion steps from §8.1 are Target
state; the MVP proves the parse->chunk->embed->index path end to end. The store
is injected so the same pipeline targets in-memory (tests), pgvector (dev), or
Vertex Vector Search (later).
"""
from __future__ import annotations

from dataclasses import dataclass

from .chunker import structure_aware_chunk
from .embeddings import Embedder
from .parser import parse
from .types import Chunk
from .vectorstore import VectorStore


@dataclass
class IngestResult:
    doc_id: str
    chunks: int
    embedded: int
    indexed: int


def ingest(
    source_path: str,
    *,
    doc_id: str,
    brand: str,
    model: str,
    url: str,
    embedder: Embedder,
    store: VectorStore,
    locale: str = "en",
) -> IngestResult:
    text = parse(source_path)
    chunks: list[Chunk] = structure_aware_chunk(
        text, doc_id=doc_id, brand=brand, model=model, url=url, locale=locale
    )

    vectors = embedder.embed([c.text for c in chunks])
    for chunk, vec in zip(chunks, vectors):
        chunk.vector = vec

    indexed = store.upsert(chunks)
    return IngestResult(
        doc_id=doc_id, chunks=len(chunks), embedded=len(vectors), indexed=indexed
    )
