"""
Routing gate.

Turns a Decision into a dispatch to exactly one downstream handler. This is the
chokepoint that guarantees a blocked or physical-risk message can never reach
the orchestrator (the LLM): `blocked` is checked FIRST and short-circuits, and
T3 routes to escalation before any generation path.

chat-api (Milestone 5) reuses `route()` with real handlers. The safety test
suite reuses it with a spy orchestrator to prove the LLM path is never taken.
"""
from collections.abc import Callable
from typing import TypeVar

from .classifier import Decision, Tier

R = TypeVar("R")


def route(
    decision: Decision,
    *,
    on_blocked: Callable[[Decision], R],
    to_escalation: Callable[[Decision], R],
    to_dosing: Callable[[Decision], R],
    to_orchestrator: Callable[[Decision], R],
) -> R:
    """Dispatch a classified decision. Only an un-blocked Tier-1 decision ever
    reaches `to_orchestrator` (the LLM)."""
    # 1) Hard block — disclaimer only. The LLM and all downstream services are
    #    unreachable from here. This branch MUST come first.
    if decision.blocked:
        return on_blocked(decision)

    # 2) Physical risk — human escalation, never generation.
    if decision.tier == Tier.T3:
        return to_escalation(decision)

    # 3) Chemistry/dosing — deterministic calculator, never the LLM.
    if decision.tier == Tier.T2:
        return to_dosing(decision)

    # 4) Informational (Tier 1) — the only path that reaches the orchestrator.
    return to_orchestrator(decision)
