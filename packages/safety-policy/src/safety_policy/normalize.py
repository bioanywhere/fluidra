"""
Text normalization + PII redaction.

SAFETY-CRITICAL: these transforms run BEFORE pattern matching. The de-accenting
and de-leeting here are what make the hard-block resistant to obfuscation, so
they are part of the reviewed, versioned policy — not incidental string code.

Two transforms with different jobs:
  - normalize()      : lowercase + strip accents (NFKD). Used for matching. The
                       leet-tolerant patterns in patterns.py absorb leetspeak,
                       so normalize() deliberately does NOT resolve digits here.
  - deleet_basic()   : best-effort digit/symbol -> letter mapping. Used by the
                       Tier-3 physical-risk matcher and as a mixing backstop,
                       where plain regexes (not per-letter patterns) are used.
  - redact()         : replace PII (email, phone) with placeholders BEFORE the
                       text is persisted, logged, or sent downstream.
"""
import re
import unicodedata

# PII patterns — redaction happens upstream of all persistence and logging.
PII_PATTERNS: dict[str, str] = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "phone": r"\+?\d[\d\s().\-]{7,}\d",
}
_PII_COMPILED = {name: re.compile(pat, re.I) for name, pat in PII_PATTERNS.items()}

# Best-effort single-character leet map for the de-leet backstop. Ambiguous
# characters (1 -> i or l) are resolved to the most common letter; the
# per-letter patterns in patterns.py handle the ambiguity properly for mixing.
_LEET_TRANSLATE = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "8": "b",
        "9": "g",
        "@": "a",
        "$": "s",
        "|": "i",
        "!": "i",
        "+": "t",
    }
)


def normalize(text: str) -> str:
    """Lowercase + strip diacritics (so 'ácido' -> 'acido', 'LEJÍA' -> 'lejia')."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower()


def deleet_basic(text: str) -> str:
    """Apply the best-effort leet->letter map. Use on already-normalized text."""
    return text.translate(_LEET_TRANSLATE)


def redact(text: str) -> str:
    """Replace emails/phones with [email]/[phone]. Idempotent; preserves the rest."""
    for name, pat in _PII_COMPILED.items():
        text = pat.sub(f"[{name}]", text)
    return text
