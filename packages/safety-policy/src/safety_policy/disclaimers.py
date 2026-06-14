"""
Disclaimer / refusal strings shown to the user.

SAFETY-CRITICAL — wording is reviewed by legal. Do not edit casually.
Versioned together with the package (see __init__.VERSION).
"""

# Shown when a chemical-mixing request is hard-blocked (Tier 2, blocked=True).
DISCLAIMER_CHEMICAL_MIXING = (
    "I can't help with mixing or combining pool chemicals — some combinations "
    "(for example acid with chlorine products) release toxic gas and can be "
    "fatal. Always add each chemical to water separately, never to another "
    "chemical, and follow the product label. If you've already combined "
    "chemicals, move to fresh air and contact your local poison control or "
    "emergency services."
)

# Shown when a physical-risk signal is detected (Tier 3, escalate).
DISCLAIMER_PHYSICAL_RISK = (
    "This may be a safety risk. Please stop using the equipment now and keep "
    "clear of it. I'm connecting you with a Fluidra specialist who will have "
    "your conversation context and follow up. If anyone is in immediate danger "
    "or you smell gas, leave the area and call your local emergency number."
)

# Shown when the orchestrator cannot ground an answer (Tier 1 fallback).
DISCLAIMER_ESCALATION = (
    "I can't answer that confidently from the official manuals. "
    "Let me connect you with a Fluidra specialist."
)
