"""
LLM layer.

`VertexGeminiLLM` calls Gemini (gemini-2.0-flash) via Vertex AI; imported lazily
so the module loads without the GCP SDK. `FakeLLM` is a deterministic,
grounded-by-construction stand-in so CI never hits Vertex. Both satisfy the same
`LLM` protocol; the graph doesn't know which it has.

`build_prompt()` assembles the system persona (from the versioned prompts
package) + the retrieved context + the user query — used by the real model.
"""
from __future__ import annotations

import os
from typing import Protocol

from prompts import get_prompt

from ingestion_worker.types import Chunk

from .text import content_words

GEMINI_FLASH = "gemini-2.0-flash"
GEMINI_PRO = "gemini-2.0-pro"

_REFUSAL = "I don't have that information in the official manuals."


class LLM(Protocol):
    name: str

    def generate(self, *, system: str, chunks: list[Chunk], query: str) -> str: ...


def route_model(query: str) -> str:
    """Pick a model for the query (blueprint: Flash for simple, Pro for complex).
    MVP routes everything to Flash; the hook is here for cost/latency tuning."""
    return GEMINI_FLASH


def _format_context(chunks: list[Chunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(
            f"[{i}] doc_id={c.doc_id} | section={c.section}\n{c.text}"
        )
    return "\n\n".join(blocks)


def build_prompt(system: str, chunks: list[Chunk], query: str) -> str:
    """Assemble the full text prompt sent to Gemini."""
    context = _format_context(chunks) if chunks else "(no relevant manual sections found)"
    return (
        f"{system}\n\n"
        f"## Context (official manual excerpts)\n{context}\n\n"
        f"## User question\n{query}\n\n"
        f"## Answer (only from the context above; if not answerable, say so)\n"
    )


class FakeLLM:
    """Deterministic test LLM. If the context actually covers the query it
    answers using the supporting chunk's own sentences (so the answer is
    grounded by construction); otherwise it returns a refusal that the
    groundedness gate will reject -> fallback. This mirrors how the real model,
    constrained to the context, behaves on in- vs out-of-scope questions."""

    name = "fake"
    _MIN_QUERY_OVERLAP = 1   # query must share >=1 content word with a chunk

    def generate(self, *, system: str, chunks: list[Chunk], query: str) -> str:
        qwords = content_words(query)
        # Respect retrieval ranking (hybrid dense+keyword already put the best
        # chunk first): answer from the highest-ranked chunk that is actually
        # relevant to the query; refuse if none are -> groundedness gate -> fallback.
        for chunk in chunks:
            if len(qwords & content_words(chunk.text)) >= self._MIN_QUERY_OVERLAP:
                return _answer_from_chunk(chunk)
        return _REFUSAL


def _answer_from_chunk(chunk: Chunk) -> str:
    """Build a grounded answer from a chunk's own text (drop the [section] tag)."""
    body_lines = [ln for ln in chunk.text.splitlines() if not ln.strip().startswith("[")]
    body = " ".join(ln.strip() for ln in body_lines if ln.strip())
    # Keep it concise: first two sentences of the section.
    import re

    sentences = re.split(r"(?<=[.!?])\s+", body)
    return " ".join(sentences[:2]).strip() or body


class VertexGeminiLLM:
    """Gemini via Vertex AI. Lazily constructed."""

    def __init__(self, model: str | None = None, location: str | None = None):
        import vertexai
        from vertexai.generative_models import GenerativeModel  # lazy

        # Model id is env-driven (GEMINI_MODEL_FAST) so changing it never needs a
        # rebuild — and availability varies by region.
        model = model or os.getenv("GEMINI_MODEL_FAST", GEMINI_FLASH)
        self.name = model
        project = os.getenv("GCP_PROJECT_ID")
        location = location or os.getenv("VERTEX_LOCATION", "europe-west1")
        vertexai.init(project=project, location=location)
        self._model = GenerativeModel(model)

    def generate(self, *, system: str, chunks: list[Chunk], query: str) -> str:
        prompt = build_prompt(system, chunks, query)
        resp = self._model.generate_content(prompt)
        return (resp.text or "").strip()


def get_llm() -> LLM:
    """Select the LLM backend.  LLM_BACKEND = fake | vertex | auto (default)."""
    backend = os.getenv("LLM_BACKEND", "auto").lower()
    if backend == "fake":
        return FakeLLM()
    if backend == "vertex":
        return VertexGeminiLLM()
    try:
        return VertexGeminiLLM()
    except Exception:
        return FakeLLM()
