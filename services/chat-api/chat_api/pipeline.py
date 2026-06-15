"""
Turn-handling pipeline (blueprint §1.4) — DB-free so it is reused by both
/v1/chat and the eval-runner.

Order is the safety order: classify (deterministic, pre-LLM) -> route. Only the
Tier-1 path reaches the orchestrator (the LLM). Tier-2 dosing uses the
deterministic calculator; Tier-3 and hard-blocked mixing never generate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from shared_types import Citation

from safety_gateway.classifier import classify
from safety_gateway.router import route
from safety_policy import DISCLAIMER_CHEMICAL_MIXING, DISCLAIMER_PHYSICAL_RISK

from dosing_service import build_dosing_card
from orchestrator.graph import answer as orchestrate


@dataclass
class TurnOutcome:
    tier: str                       # T1 | T2 | T3
    type: str                       # answer | dosing_prompt | escalation
    content: str
    citations: list[Citation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    intent: str = ""
    blocked: bool = False
    rule: str | None = None
    groundedness: float | None = None
    escalated: bool = False


def handle_turn(message: str, *, store, embedder, llm, intent_model) -> TurnOutcome:
    """Classify a message and route it to exactly one handler."""
    decision = classify(message, intent_model)

    def on_blocked(d) -> TurnOutcome:
        # Hard-blocked chemical mixing — safety refusal, never reaches the LLM.
        return TurnOutcome(
            tier=d.tier.value, type="answer", content=DISCLAIMER_CHEMICAL_MIXING,
            warnings=[DISCLAIMER_CHEMICAL_MIXING], intent=d.intent,
            blocked=True, rule=d.rule,
        )

    def to_escalation(d) -> TurnOutcome:
        return TurnOutcome(
            tier="T3", type="escalation", content=DISCLAIMER_PHYSICAL_RISK,
            warnings=[DISCLAIMER_PHYSICAL_RISK], intent=d.intent,
            rule=d.rule, escalated=True,
        )

    def to_dosing(d) -> TurnOutcome:
        card = build_dosing_card(d.redacted_text)
        return TurnOutcome(
            tier="T2", type="dosing_prompt", content=card.content,
            warnings=card.warnings, intent="dosing",
        )

    def to_orchestrator(d) -> TurnOutcome:
        # The ONLY path that reaches the LLM. Uses redacted text (no PII).
        res = orchestrate(d.redacted_text, store=store, embedder=embedder, llm=llm)
        return TurnOutcome(
            tier="T1",
            type="escalation" if res.escalated else "answer",
            content=res.answer,
            citations=list(res.citations),
            intent=d.intent,
            groundedness=res.groundedness,
            escalated=res.escalated,
        )

    return route(
        decision,
        on_blocked=on_blocked,
        to_escalation=to_escalation,
        to_dosing=to_dosing,
        to_orchestrator=to_orchestrator,
    )
