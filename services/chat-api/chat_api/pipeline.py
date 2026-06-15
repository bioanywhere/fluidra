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

from observability import set_attributes, span
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
    """Classify a message and route it to exactly one handler.

    The whole turn is one trace: safety.classify -> (orchestrator.retrieve ->
    generate -> verify) for Tier-1, with tier/intent/groundedness on the span
    (blueprint §9.2)."""
    with span("chat.turn") as turn:
        with span("safety.classify") as classify_span:
            decision = classify(message, intent_model)
            set_attributes(
                classify_span,
                **{
                    "safety.tier": decision.tier.value,
                    "safety.intent": decision.intent,
                    "safety.blocked": decision.blocked,
                    "safety.rule": decision.rule or "",
                    "safety.policy_version": decision.policy_version,
                },
            )
        set_attributes(
            turn,
            **{
                "safety.tier": decision.tier.value,
                "safety.intent": decision.intent,
                "safety.blocked": decision.blocked,
            },
        )
        outcome = _route_decision(
            decision, store=store, embedder=embedder, llm=llm
        )
        set_attributes(
            turn,
            **{
                "response.type": outcome.type,
                "response.tier": outcome.tier,
                "response.escalated": outcome.escalated,
                "response.citations": len(outcome.citations),
            },
        )
        if outcome.groundedness is not None:
            set_attributes(turn, **{"ai.groundedness": outcome.groundedness})
        return outcome


def _route_decision(decision, *, store, embedder, llm) -> TurnOutcome:
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
