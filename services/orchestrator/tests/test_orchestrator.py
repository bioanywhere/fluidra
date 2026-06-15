"""
Milestone 4 verification: the orchestrator returns grounded, cited answers for
in-scope questions and routes out-of-scope questions to a graceful fallback
(never a hallucinated answer).
"""
from fastapi.testclient import TestClient

from orchestrator.graph import answer
from orchestrator.groundedness import groundedness_score
from orchestrator.citations import bind_citations
from orchestrator.llm import FakeLLM


def test_code_125_returns_grounded_answer_with_citation(rag):
    store, embedder, llm = rag
    res = answer("my salt system shows code 125", store=store, embedder=embedder, llm=llm)

    assert res.grounded is True
    assert res.escalated is False
    assert res.groundedness >= 0.8
    assert res.answer and "flow" in res.answer.lower()

    # cited to the ingested manual, with the code-125 section
    assert res.citations, "expected at least one citation"
    assert all(c.doc_id == "H0567500" for c in res.citations)
    assert any("125" in c.section for c in res.citations)


def test_out_of_scope_routes_to_fallback(rag):
    store, embedder, llm = rag
    res = answer("what is the capital of France", store=store, embedder=embedder, llm=llm)

    assert res.grounded is False
    assert res.escalated is True
    assert res.citations == []
    assert "specialist" in res.answer.lower()


def test_pool_profile_filter_still_answers(rag):
    """A matching equipment profile biases retrieval but still answers."""
    store, embedder, llm = rag
    res = answer(
        "what does code 125 mean", store=store, embedder=embedder, llm=llm,
        pool_profile={"brand": "Jandy"},
    )
    assert res.grounded is True
    assert any("125" in c.section for c in res.citations)


def test_groundedness_scoring_directions(rag):
    store, embedder, _llm = rag
    chunks = [s.chunk for s in __import__("ingestion_worker.retrieval", fromlist=["retrieve"]).retrieve(
        store, embedder, "code 125", top_k=6
    )]
    grounded_answer = chunks[0].text.split("]", 1)[-1].strip()  # the chunk body
    assert groundedness_score(grounded_answer, chunks) >= 0.8
    assert groundedness_score("The warranty covers lightning strikes for ten years.", chunks) < 0.8


def test_bind_citations_dedups_and_resolves(rag):
    store, embedder, _llm = rag
    from ingestion_worker.retrieval import retrieve
    chunks = [s.chunk for s in retrieve(store, embedder, "code 125", top_k=6)]
    answer_text = chunks[0].text
    cites = bind_citations(answer_text, chunks)
    assert cites
    keys = [(c.doc_id, c.section) for c in cites]
    assert len(keys) == len(set(keys)), "citations must be de-duplicated"


def test_answer_endpoint_offline(rag, monkeypatch):
    """HTTP path works with injected in-memory deps (no Postgres/Vertex)."""
    store, embedder, llm = rag
    from orchestrator import main

    main._deps.clear()
    main._deps.update({"store": store, "embedder": embedder, "llm": llm})

    client = TestClient(main.app)
    r = client.post("/v1/answer", json={"query": "my salt system shows code 125"})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["citations"] and any("125" in c["section"] for c in body["citations"])

    main._deps.clear()
