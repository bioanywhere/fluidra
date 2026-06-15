"""Small lexical helpers shared by groundedness + citation binding."""
from __future__ import annotations

import re

# Minimal stoplist — enough to stop generic words from inflating overlap scores.
_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "is", "are", "was",
    "be", "to", "of", "in", "on", "for", "with", "as", "at", "by", "it",
    "this", "that", "these", "those", "you", "your", "i", "we", "they",
    "do", "does", "can", "could", "should", "would", "will", "may", "my",
    "me", "from", "about", "into", "out", "up", "down", "so", "not", "no",
    "what", "which", "when", "how", "why", "where", "who", "have", "has",
}


def content_words(text: str) -> set[str]:
    """Lowercased alphanumeric tokens (len >= 2), minus stopwords."""
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if len(t) >= 2 and t not in _STOP
    }


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]
