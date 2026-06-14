"""
Structure-aware chunking (blueprint §6.2).

Splits on manual section headings (not fixed token windows) so a chunk is a
coherent unit — critical for fault codes, where the answer is one self-contained
section. Each chunk carries a section breadcrumb and full provenance metadata.

Long sections are further split into ~target_tokens windows with ~15% overlap so
no chunk exceeds the embedding context while preserving continuity.
"""
from __future__ import annotations

import re

from .types import Chunk

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def _approx_tokens(text: str) -> int:
    # Cheap, dependency-free heuristic (~0.75 words/token).
    return int(len(text.split()) / 0.75)


def _split_long(text: str, target_tokens: int, overlap: float) -> list[str]:
    """Split an over-long section into overlapping word windows."""
    words = text.split()
    target_words = max(1, int(target_tokens * 0.75))
    if len(words) <= target_words:
        return [text]
    step = max(1, int(target_words * (1 - overlap)))
    windows = []
    for start in range(0, len(words), step):
        window = words[start : start + target_words]
        if window:
            windows.append(" ".join(window))
        if start + target_words >= len(words):
            break
    return windows


def structure_aware_chunk(
    text: str,
    *,
    doc_id: str,
    brand: str,
    model: str,
    url: str,
    locale: str = "en",
    target_tokens: int = 450,
    overlap: float = 0.15,
) -> list[Chunk]:
    """Parse Markdown headings into a section tree and emit chunks with breadcrumbs."""
    lines = text.splitlines()
    heading_stack: list[tuple[int, str]] = []  # (level, title)
    sections: list[tuple[str, list[str]]] = []  # (breadcrumb, body_lines)
    current_body: list[str] = []

    def breadcrumb() -> str:
        return " > ".join(title for _, title in heading_stack) or "(intro)"

    def flush():
        body = "\n".join(current_body).strip()
        if body:
            sections.append((breadcrumb(), current_body.copy()))

    for line in lines:
        m = _HEADING.match(line)
        if m:
            flush()
            current_body.clear()
            level = len(m.group(1))
            title = m.group(2).strip()
            # pop deeper-or-equal levels, then push this heading
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
        else:
            current_body.append(line)
    flush()

    chunks: list[Chunk] = []
    idx = 0
    for section, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        # Prepend the section breadcrumb so the chunk text is self-describing
        # (helps both embeddings and the LLM cite the right section).
        for window in _split_long(body, target_tokens, overlap):
            chunk_text = f"[{section}]\n{window}"
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    brand=brand,
                    model=model,
                    section=section,
                    url=url,
                    text=chunk_text,
                    chunk_index=idx,
                    locale=locale,
                )
            )
            idx += 1
    return chunks
