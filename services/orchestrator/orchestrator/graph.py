r"""
Orchestration graph (blueprint §6.1) — an explicit LangGraph, not a free agent
loop:

    retrieve -> generate -> verify --(grounded >= 0.8)--> END
                                   \--(otherwise)-------> fallback -> END

Dependencies (vector store, embedder, LLM) are injected so the same graph runs
against in-memory + fake-LLM in tests and pgvector + Gemini in dev/prod.
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from observability import langfuse_trace, set_attributes, span
from safety_policy import DISCLAIMER_ESCALATION
from prompts import get_prompt

from ingestion_worker.embeddings import Embedder
from ingestion_worker.retrieval import retrieve as retrieve_chunks
from ingestion_worker.vectorstore import VectorStore

from .citations import bind_citations
from .groundedness import groundedness_score
from .llm import LLM
from .state import OrchestratorResult, TurnState

GROUNDEDNESS_THRESHOLD = 0.8


def _brand_filters(pool_profile: dict) -> dict | None:
    """Bias retrieval to the user's declared equipment (blueprint §6.2)."""
    filters = {}
    for key in ("brand", "model"):
        if pool_profile.get(key):
            filters[key] = pool_profile[key]
    return filters or None


def build_graph(
    *,
    store: VectorStore,
    embedder: Embedder,
    llm: LLM,
    persona: str | None = None,
    threshold: float = GROUNDEDNESS_THRESHOLD,
    top_k: int = 6,
):
    """Compile the orchestration graph with its dependencies bound in."""
    persona = persona if persona is not None else get_prompt("system_persona")

    def retrieve(state: TurnState) -> TurnState:
        with span("orchestrator.retrieve") as s:
            filters = _brand_filters(state.get("pool_profile") or {})
            scored = retrieve_chunks(store, embedder, state["query"], top_k=top_k, filters=filters)
            state["chunks"] = [sc.chunk for sc in scored]
            set_attributes(s, **{"rag.chunks": len(state["chunks"]), "rag.embedder": embedder.name})
        return state

    def generate(state: TurnState) -> TurnState:
        with span("orchestrator.generate") as s:
            model = getattr(llm, "name", "unknown")
            answer = llm.generate(system=persona, chunks=state["chunks"], query=state["query"])
            state["answer"] = answer
            state["citations"] = bind_citations(answer, state["chunks"])
            set_attributes(s, **{"ai.model": model, "ai.answer_chars": len(answer)})
            langfuse_trace.record_generation(
                name="orchestrator.generate", prompt=state["query"],
                completion=answer, model=model,
                metadata={"chunks": len(state["chunks"])},
            )
        return state

    def verify(state: TurnState) -> TurnState:
        with span("orchestrator.verify") as s:
            score = groundedness_score(state["answer"], state["chunks"])
            state["groundedness"] = score
            state["grounded"] = score >= threshold
            set_attributes(s, **{"ai.groundedness": score, "ai.grounded": state["grounded"]})
        return state

    def fallback(state: TurnState) -> TurnState:
        # Graceful escalation instead of an ungrounded (hallucinated) answer.
        state["answer"] = DISCLAIMER_ESCALATION
        state["citations"] = []
        state["escalated"] = True
        return state

    g = StateGraph(TurnState)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_node("verify", verify)
    g.add_node("fallback", fallback)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "verify")
    g.add_conditional_edges(
        "verify",
        lambda s: "ok" if s["grounded"] else "fallback",
        {"ok": END, "fallback": "fallback"},
    )
    g.add_edge("fallback", END)
    return g.compile()


def answer(
    query: str,
    *,
    store: VectorStore,
    embedder: Embedder,
    llm: LLM,
    pool_profile: dict | None = None,
    threshold: float = GROUNDEDNESS_THRESHOLD,
    top_k: int = 6,
) -> OrchestratorResult:
    """Run one turn through the graph and return a structured result."""
    app = build_graph(
        store=store, embedder=embedder, llm=llm, threshold=threshold, top_k=top_k
    )
    final: TurnState = app.invoke(
        {
            "query": query,
            "pool_profile": pool_profile or {},
            "chunks": [],
            "answer": "",
            "citations": [],
            "grounded": False,
            "groundedness": 0.0,
            "escalated": False,
        }
    )
    return OrchestratorResult(
        answer=final["answer"],
        citations=final["citations"],
        grounded=final["grounded"],
        groundedness=final["groundedness"],
        escalated=final["escalated"],
    )
