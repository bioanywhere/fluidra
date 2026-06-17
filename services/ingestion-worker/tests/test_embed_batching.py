"""VertexEmbedder batches get_embeddings under the 250-instance Vertex cap."""
from ingestion_worker.embeddings import VertexEmbedder


class _FakeModel:
    def __init__(self, cap=250):
        self.cap = cap
        self.batch_sizes = []

    def get_embeddings(self, texts):
        self.batch_sizes.append(len(texts))
        if len(texts) > self.cap:  # mimic Vertex's "250 instance(s) allowed" 400
            raise ValueError(f"{self.cap} instance(s) allowed. Actual: {len(texts)}")
        return [type("E", (), {"values": [0.0, 1.0]})() for _ in texts]


def _embedder(model):
    e = VertexEmbedder.__new__(VertexEmbedder)  # bypass Vertex SDK init
    e._model = model
    return e


def test_batches_stay_under_cap_and_cover_all():
    model = _FakeModel(cap=250)
    e = _embedder(model)
    out = e.embed(["chunk"] * 366)
    assert len(out) == 366
    assert max(model.batch_sizes) <= 250
    assert all(v == [0.0, 1.0] for v in out)


def test_adaptive_shrink_on_limit_error():
    # A stricter cap forces the adaptive fallback to shrink and still succeed.
    model = _FakeModel(cap=40)
    e = _embedder(model)
    out = e.embed(["chunk"] * 130)
    assert len(out) == 130
    assert 100 in model.batch_sizes  # first attempt, before shrinking
    successful = [b for b in model.batch_sizes if b <= 40]
    assert sum(successful) == 130  # shrunk batches still cover every chunk
