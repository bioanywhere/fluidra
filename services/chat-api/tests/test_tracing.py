"""
Turn-level tracing (blueprint §9.2): one trace per turn with classify -> retrieve
-> generate -> verify spans carrying tier/intent/groundedness. Also asserts that
a hard-blocked turn produces NO orchestrator (LLM) spans — observability backing
the safety guarantee.
"""
from observability import configure_in_memory
from ingestion_worker.corpus import ingest_corpus
from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.vectorstore import InMemoryVectorStore
from orchestrator.llm import FakeLLM
from safety_gateway.intent import KeywordIntentModel

from chat_api.pipeline import handle_turn


def _rag():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    ingest_corpus(store, embedder)
    return store, embedder, FakeLLM()


def test_t1_turn_emits_full_trace():
    exporter = configure_in_memory()
    store, embedder, llm = _rag()
    handle_turn(
        "my salt system shows code 125",
        store=store, embedder=embedder, llm=llm, intent_model=KeywordIntentModel(),
    )
    spans = {s.name: s for s in exporter.get_finished_spans()}
    for expected in ("chat.turn", "safety.classify", "orchestrator.retrieve",
                     "orchestrator.generate", "orchestrator.verify"):
        assert expected in spans, f"missing span {expected}"

    turn = spans["chat.turn"]
    assert turn.attributes["safety.tier"] == "T1"
    assert turn.attributes["response.type"] == "answer"
    assert turn.attributes["ai.groundedness"] >= 0.8
    assert spans["orchestrator.verify"].attributes["ai.grounded"] is True
    assert spans["orchestrator.retrieve"].attributes["rag.chunks"] > 0


def test_blocked_turn_has_no_llm_spans():
    exporter = configure_in_memory()
    store, embedder, llm = _rag()
    handle_turn(
        "can I mix muriatic acid and chlorine",
        store=store, embedder=embedder, llm=llm, intent_model=KeywordIntentModel(),
    )
    names = [s.name for s in exporter.get_finished_spans()]
    assert "chat.turn" in names
    # the LLM path must be unreachable for a hard-blocked mixing request
    assert "orchestrator.generate" not in names
    assert "orchestrator.retrieve" not in names
