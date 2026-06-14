"""
The deterministic safety classifier (blueprint §5.5).

This is the single most important module in the system and is deliberately the
least "clever" code in the repo: pure rules/regex that execute BEFORE any model
call and cannot be prompt-injected away. The LLM is only reachable on the T1
path returned here.

All dangerous-path detection (mixing, physical risk) and the patterns live in
the versioned `safety_policy` package so they change under legal review without
touching this routing logic.
"""
from dataclasses import dataclass
from enum import Enum

import safety_policy as policy


class Tier(str, Enum):
    """Mirrors shared_types.Tier (same string values) — kept local so the
    safety classifier has no dependency that could change its behavior."""
    T1 = "T1"   # informational — answer freely with citations
    T2 = "T2"   # chemistry/dosing — structured flow only (or hard-blocked)
    T3 = "T3"   # physical risk — diagnose & escalate, never LLM repair steps


@dataclass
class Decision:
    tier: Tier
    intent: str
    blocked: bool
    rule: str | None
    redacted_text: str
    policy_version: str = policy.VERSION


def classify(text: str, intent_model) -> Decision:
    """
    Classify a user message into a tier + routing decision.

    Order is critical and must not change:
      1. Hard safety blocks (chemical mixing)      -> blocked, never sees LLM.
      2. Physical-risk signals                     -> escalate to a human.
      3. Intent routing (dosing vs everything else)-> T2 dosing flow or T1.

    Steps 1 and 2 are deterministic and run before the intent model, so an
    adversarial prompt cannot route itself around them.
    """
    redacted = policy.redact(text)

    # 1) Hard safety block — highest priority, deterministic, pre-LLM.
    if policy.detect_chemical_mixing(text):
        return Decision(
            tier=Tier.T2,
            intent="chemical_mixing",
            blocked=True,
            rule="mixing_block",
            redacted_text=redacted,
        )

    # 2) Physical risk -> human escalation (never LLM repair instructions).
    if policy.detect_physical_risk(text):
        return Decision(
            tier=Tier.T3,
            intent="physical_risk",
            blocked=False,
            rule="escalate",
            redacted_text=redacted,
        )

    # 3) Intent classification (keyword/zero-shot stub for now) for routing.
    intent = intent_model.predict(redacted)
    if intent == "dosing":
        return Decision(
            tier=Tier.T2,
            intent="dosing",
            blocked=False,
            rule="dosing_flow",
            redacted_text=redacted,
        )

    return Decision(
        tier=Tier.T1,
        intent=intent,
        blocked=False,
        rule=None,
        redacted_text=redacted,
    )
