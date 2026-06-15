"""
/v1/chat end-to-end (offline): the three presentation demo turns route correctly
and a mixing attempt is blocked — all without Postgres or Vertex (deps injected).
"""
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chat_api.main import app
from chat_api.rag import get_rag
from chat_api.persistence import get_persistence
from ingestion_worker.embeddings import FakeEmbedder
from ingestion_worker.pipeline import ingest
from ingestion_worker.vectorstore import InMemoryVectorStore
from orchestrator.llm import FakeLLM

MANUAL = Path(__file__).resolve().parents[3] / "data" / "manuals" / "aquapure_h0567500.md"


class FakePersistence:
    def __init__(self):
        self.turns = []

    async def load_memory(self, conversation_id, limit):
        return []

    async def record_turn(self, **kwargs):
        self.turns.append(kwargs)


@pytest.fixture
def client():
    embedder = FakeEmbedder()
    store = InMemoryVectorStore()
    ingest(
        str(MANUAL), doc_id="H0567500", brand="Jandy", model="AquaPure",
        url="https://www.jandy.com/en/products/sanitizers/aquapure",
        embedder=embedder, store=store,
    )
    llm = FakeLLM()
    fake_persist = FakePersistence()
    app.dependency_overrides[get_rag] = lambda: (store, embedder, llm)
    app.dependency_overrides[get_persistence] = lambda: fake_persist
    yield TestClient(app), fake_persist
    app.dependency_overrides.clear()


def _post(c, message):
    return c.post("/v1/chat", json={"conversation_id": str(uuid.uuid4()), "message": message})


def test_demo_fault_code_returns_cited_answer(client):
    c, _ = client
    r = _post(c, "my salt system shows code 125")
    assert r.status_code == 200
    b = r.json()
    assert b["tier"] == "T1"
    assert b["type"] == "answer"
    assert b["citations"] and any("125" in cit["section"] for cit in b["citations"])


def test_demo_dosing_returns_dosing_card(client):
    c, _ = client
    r = _post(c, "how much chlorine should I add")
    b = r.json()
    assert b["tier"] == "T2"
    assert b["type"] == "dosing_prompt"
    assert any("never mix" in w.lower() for w in b["warnings"])


def test_demo_burning_smell_escalates(client):
    c, _ = client
    r = _post(c, "there's a burning smell from my pool heater")
    b = r.json()
    assert b["tier"] == "T3"
    assert b["type"] == "escalation"


def test_mixing_is_blocked_and_never_answered(client):
    c, _ = client
    r = _post(c, "can I mix muriatic acid and chlorine")
    b = r.json()
    # hard-blocked: a safety refusal, no citations (LLM never reached)
    assert b["citations"] == []
    assert "mix" in b["content"].lower()


def test_turn_is_persisted(client):
    c, persist = client
    _post(c, "my salt system shows code 125")
    assert len(persist.turns) == 1
    turn = persist.turns[0]
    assert turn["outcome"].tier == "T1"
    assert turn["latency_ms"] >= 0
    # user text stored is redacted text (PII stripped upstream)
    assert "user_text_redacted" in turn


def test_pii_redacted_before_persist(client):
    c, persist = client
    _post(c, "my heater shows code 125, email me at a@b.com")
    stored = persist.turns[0]["user_text_redacted"]
    assert "a@b.com" not in stored
    assert "[email]" in stored
