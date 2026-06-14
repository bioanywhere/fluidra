"""
Embeddings.

`VertexEmbedder` wires Vertex AI `text-embedding-005` via Application Default
Credentials (blueprint §2). `FakeEmbedder` is a deterministic, dependency-free
fallback so the pipeline and tests run fully offline. `get_embedder()` selects
based on env + availability, so CI never needs Vertex.

  EMBEDDING_BACKEND = fake | vertex   (default: auto)
  - auto: use Vertex if the lib imports AND credentials resolve, else fake.
"""
from __future__ import annotations

import hashlib
import os
from typing import Protocol

import numpy as np

_FAKE_DIM = 256


class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedder:
    """Deterministic hashed bag-of-words embedding. Shared tokens -> higher
    cosine similarity, which is enough to retrieve the right manual section
    offline (e.g. a query with '125' matches the '125' chunk)."""

    name = "fake"

    def __init__(self, dim: int = _FAKE_DIM):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float64)
        tokens = _tokenize(text)
        for tok in tokens:
            h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()


class VertexEmbedder:
    """Vertex AI text-embedding-005 via ADC. Imported lazily; only constructed
    when actually used so the module imports without the GCP SDK present."""

    name = "vertex"
    dim = 768  # text-embedding-005 dimensionality

    def __init__(self, model: str = "text-embedding-005", location: str | None = None):
        from vertexai.language_models import TextEmbeddingModel  # lazy
        import vertexai

        project = os.getenv("GCP_PROJECT_ID")
        location = location or os.getenv("VERTEX_LOCATION", "europe-west1")
        vertexai.init(project=project, location=location)
        self._model = TextEmbeddingModel.from_pretrained(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        results = self._model.get_embeddings(texts)
        return [r.values for r in results]


def get_embedder() -> Embedder:
    backend = os.getenv("EMBEDDING_BACKEND", "auto").lower()
    if backend == "fake":
        return FakeEmbedder()
    if backend == "vertex":
        return VertexEmbedder()
    # auto
    try:
        return VertexEmbedder()
    except Exception:
        return FakeEmbedder()


def _tokenize(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())
