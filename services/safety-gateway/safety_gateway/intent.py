"""
Intent router (MVP stub).

A keyword classifier that returns one of: "dosing", "fault_code",
"maintenance", "general". Per the blueprint this is later replaced by a small
fine-tuned / zero-shot model — the interface (`.predict(text) -> str`) stays
the same so the classifier call-site never changes.

Only "dosing" affects safety routing (-> Tier 2 structured flow). The others
are all informational (Tier 1); the label is still useful for retrieval biasing
and analytics downstream.
"""
import re

# Order matters: dosing is checked first because it gates the deterministic
# calculator path. Patterns are matched against PII-redacted, lowercased text.
_DOSING = re.compile(
    r"\b(dose|dosing|dosage|how much|how many|ppm|raise|lower|increase|"
    r"decrease|adjust|balance|shock|add)\b.*\b(ph|alkalinity|chlorine|"
    r"chlorinate|cyanuric|stabili[sz]er|calcium|hardness|salt|acid|"
    r"bicarb|soda ash|cloro|alcalinidad|sal)\b",
    re.I,
)
_DOSING_SIMPLE = re.compile(
    r"\b(how much (chlorine|acid|salt|stabili[sz]er|soda ash|bicarb)|"
    r"shock (the|my) pool|chlorine (dose|dosage)|"
    r"cu[aá]nto cloro|dosis)\b",
    re.I,
)
_FAULT = re.compile(
    r"\b(fault|error|err|code|alarm|alert|flash(ing)?|blink(ing)?|"
    r"warning|service code|check system|no flow|low flow|"
    r"e\d{1,3}|err\d{1,3}|code\s*\d{1,4})\b",
    re.I,
)
_MAINTENANCE = re.compile(
    r"\b(clean(ing)?|backwash|filter|cartridge|brush|vacuum|skim(mer)?|"
    r"prime|winteri[sz]e|maintenance|schedule|how often|replace|"
    r"o-?ring|gasket|lubricat)\b",
    re.I,
)


class KeywordIntentModel:
    """Deterministic keyword intent classifier. Swappable for a real model."""

    def predict(self, text: str) -> str:
        if _DOSING.search(text) or _DOSING_SIMPLE.search(text):
            return "dosing"
        if _FAULT.search(text):
            return "fault_code"
        if _MAINTENANCE.search(text):
            return "maintenance"
        return "general"
