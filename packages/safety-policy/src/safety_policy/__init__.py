"""
safety-policy — versioned safety patterns, detectors, and disclaimer strings.

THIS PACKAGE IS SAFETY-CRITICAL.
Changes require legal + safety review. The VERSION below is recorded in audit
logs (SAFETY_POLICY_VERSION) so every blocked/escalated decision is traceable
to the exact policy that produced it.

Layout (each file independently reviewable):
  normalize.py   — text normalization + PII redaction (pre-match transforms)
  patterns.py    — chemical term lists + leet-tolerant pattern compiler
  detect.py      — deterministic mixing / physical-risk decision logic
  disclaimers.py — user-facing refusal/escalation wording
"""

from .normalize import normalize, deleet_basic, redact, PII_PATTERNS
from .detect import detect_chemical_mixing, detect_physical_risk
from .disclaimers import (
    DISCLAIMER_CHEMICAL_MIXING,
    DISCLAIMER_PHYSICAL_RISK,
    DISCLAIMER_ESCALATION,
)
from . import patterns

# Bumped on every policy change. Mirrors SAFETY_POLICY_VERSION in env config.
VERSION = "2025.06.0"

__all__ = [
    "VERSION",
    "normalize",
    "deleet_basic",
    "redact",
    "PII_PATTERNS",
    "detect_chemical_mixing",
    "detect_physical_risk",
    "DISCLAIMER_CHEMICAL_MIXING",
    "DISCLAIMER_PHYSICAL_RISK",
    "DISCLAIMER_ESCALATION",
    "patterns",
]
