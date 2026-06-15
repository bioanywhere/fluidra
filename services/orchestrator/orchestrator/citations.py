"""
Citation binding (blueprint §6.5).

Maps the generated answer back to the chunks that support it, then resolves each
to a structured citation {doc_id, section, brand, url} the client renders as
"Source: AquaPure manual (H0567500), §Service Code 125". Chunks whose content
materially overlaps the answer are cited; results are de-duplicated by
(doc_id, section) and ordered by support strength.
"""
from __future__ import annotations

from shared_types import Citation

from ingestion_worker.types import Chunk

from .text import content_words

_MIN_SUPPORT = 0.18   # min fraction of a chunk's distinctive words echoed in the
                      # answer for that chunk to count as a source


def bind_citations(answer: str, chunks: list[Chunk]) -> list[Citation]:
    """Return structured citations for the chunks that support the answer."""
    answer_words = content_words(answer)
    if not answer_words:
        return []

    scored: list[tuple[float, Chunk]] = []
    for c in chunks:
        cw = content_words(c.text)
        if not cw:
            continue
        support = len(cw & answer_words) / len(cw)
        if support >= _MIN_SUPPORT:
            scored.append((support, c))

    scored.sort(key=lambda t: t[0], reverse=True)

    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for _support, c in scored:
        key = (c.doc_id, c.section)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(doc_id=c.doc_id, section=c.section, brand=c.brand, url=c.url)
        )
    return citations
