"""
Shared fixtures for the repo-level safety corpus.

The key fixture is `route_with_spy`: it runs a message through the REAL
classifier and the REAL routing gate, but injects a spy orchestrator that
records every call. Tests use it to prove that blocked/escalated messages never
reach the LLM path — not by inspecting the Decision alone, but by asserting the
orchestrator was physically never invoked.
"""
import pytest

from safety_gateway.classifier import classify
from safety_gateway.intent import KeywordIntentModel
from safety_gateway.router import route


class SpyOrchestrator:
    """Stand-in for the LLM path. Records calls and (optionally) explodes if hit."""

    def __init__(self, *, explode: bool = False):
        self.calls: list = []
        self._explode = explode

    def __call__(self, decision):
        self.calls.append(decision)
        if self._explode:
            raise AssertionError(
                f"LLM path was reached for a message that must never reach it: "
                f"tier={decision.tier} intent={decision.intent} rule={decision.rule}"
            )
        return {"path": "orchestrator", "decision": decision}

    @property
    def was_called(self) -> bool:
        return len(self.calls) > 0


@pytest.fixture
def intent_model() -> KeywordIntentModel:
    return KeywordIntentModel()


@pytest.fixture
def route_with_spy(intent_model):
    """
    Returns (run, spy). `run(text)` classifies + routes a message; `spy` is the
    orchestrator that would have been called on the T1 (LLM) path. The spy is
    set to explode, so any leak to the LLM fails the test immediately and loudly.
    """
    spy = SpyOrchestrator(explode=True)
    sink = {"blocked": [], "escalation": [], "dosing": []}

    def run(text: str):
        decision = classify(text, intent_model)
        result = route(
            decision,
            on_blocked=lambda d: sink["blocked"].append(d) or {"path": "blocked", "decision": d},
            to_escalation=lambda d: sink["escalation"].append(d) or {"path": "escalation", "decision": d},
            to_dosing=lambda d: sink["dosing"].append(d) or {"path": "dosing", "decision": d},
            to_orchestrator=spy,
        )
        return decision, result

    run.sink = sink  # type: ignore[attr-defined]
    return run, spy
