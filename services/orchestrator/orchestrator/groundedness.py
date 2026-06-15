"""
Groundedness verification (blueprint §6.1).

MVP implementation: a deterministic *lexical support* score — the fraction of
the answer's content, sentence by sentence, that is supported by the retrieved
context. The Target state replaces this with an LLM-as-judge (blueprint §6.6),
behind the same `groundedness_score()` interface.

The point of the node is unchanged: a poorly-supported answer (score < 0.8) is
NOT shown — the graph routes to a graceful escalation instead of hallucinating.
"""
from __future__ import annotations

from ingestion_worker.types import Chunk

from .text import content_words, split_sentences

_SENTENCE_SUPPORT = 0.5   # a sentence is "supported" if >=50% of its content
                          # words appear in the context


def groundedness_score(answer: str, chunks: list[Chunk]) -> float:
    """Return the fraction of answer sentences supported by the context (0..1)."""
    sentences = split_sentences(answer)
    if not sentences:
        return 0.0

    context_words: set[str] = set()
    for c in chunks:
        context_words |= content_words(c.text)
    if not context_words:
        return 0.0

    supported = 0
    for sentence in sentences:
        words = content_words(sentence)
        if not words:
            # punctuation-only / empty: treat as supported (no claim made)
            supported += 1
            continue
        overlap = len(words & context_words) / len(words)
        if overlap >= _SENTENCE_SUPPORT:
            supported += 1
    return supported / len(sentences)
