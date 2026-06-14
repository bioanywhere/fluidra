"""
Hybrid retrieval (blueprint §6.2).

top-k=6, metadata pre-filter to the user's equipment, and a hybrid score:
dense (embedding cosine) + a keyword boost on exact fault-code / code-like
strings. Exact codes ("125", "FAULT-HIGH LIMIT") MUST match literally — a pure
dense search can rank a semantically-similar wrong code above the exact one, so
the keyword component is not optional for this domain.
"""
from __future__ import annotations

import re

from .embeddings import Embedder
from .types import Chunk, ScoredChunk
from .vectorstore import VectorStore

DEFAULT_TOP_K = 6
_KEYWORD_WEIGHT = 0.5

# Numeric service codes (2–4 digits) and SCREAMING-CASE fault strings.
_CODE_TOKEN = re.compile(r"\b\d{2,4}\b")
_CAPS_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:[ \-][A-Z0-9]+)*\b")


def _keyword_terms(query: str) -> list[str]:
    terms = set(_CODE_TOKEN.findall(query))
    terms.update(m.strip() for m in _CAPS_TOKEN.findall(query))
    return [t for t in terms if t]


def _keyword_score(chunk_text: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    hay = chunk_text.lower()
    hits = sum(1 for t in terms if t.lower() in hay)
    return hits / len(terms)


def retrieve(
    store: VectorStore,
    embedder: Embedder,
    query: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    filters: dict | None = None,
) -> list[ScoredChunk]:
    """Return the top-k chunks for a query, re-ranked by dense + keyword score."""
    qvec = embedder.embed([query])[0]
    # Pull a wider candidate set from the dense store, then re-rank.
    candidates = store.query(qvec, max(top_k * 4, top_k), filters)

    terms = _keyword_terms(query)
    scored: list[ScoredChunk] = []
    for chunk, dense in candidates:
        kw = _keyword_score(chunk.text, terms)
        combined = dense + _KEYWORD_WEIGHT * kw
        scored.append(ScoredChunk(chunk=chunk, score=combined, dense=dense, keyword=kw))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:top_k]
