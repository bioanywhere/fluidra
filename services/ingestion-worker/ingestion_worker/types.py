"""Core data types for ingestion + retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A retrievable unit of a manual, with provenance metadata (blueprint §6.2)."""
    doc_id: str
    brand: str
    model: str
    section: str          # breadcrumb, e.g. "Service Codes > Service Code 125"
    url: str
    text: str
    chunk_index: int
    locale: str = "en"
    vector: list[float] | None = field(default=None, repr=False)

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}:{self.chunk_index}"


@dataclass
class ScoredChunk:
    """A chunk returned by retrieval, with its relevance score and a breakdown."""
    chunk: Chunk
    score: float
    dense: float = 0.0
    keyword: float = 0.0
