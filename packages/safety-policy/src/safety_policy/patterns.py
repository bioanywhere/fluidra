r"""
Safety patterns and chemical term lists.

SAFETY-CRITICAL — changes require legal + safety review. Versioned with the
package. This file is data + the pattern compiler; the decision logic that
consumes it lives in detect.py.

Design notes (why this shape):
  - The dangerous chemical names are matched with PER-LETTER leet-tolerant
    patterns built from the *canonical spelling*. Because we know the target
    word, each letter position accepts its leet equivalents, so the ambiguity
    of '1' (i vs l) disappears: in "chlorine", the l-position and the
    i-position both accept '1'. This catches "chl0r1ne", "ch1or1ne",
    "c-h-l-o-r-i-n-e", etc.
  - Small separator tolerance ([\s._-]{0,2}) between letters defeats spacing
    and punctuation obfuscation without matching across whole sentences (a
    normal word's letters break the chain).
  - For a HARD safety block, over-matching is acceptable and under-matching is
    not. The patterns are intentionally aggressive on the block path.
"""
import re

# ── Per-letter leet character classes ────────────────────────────────────────
# Only letters that appear in our target terms need entries. Ambiguous '1'/'|'
# appears in BOTH 'i' and 'l' so either letter position accepts it.
_LEET: dict[str, str] = {
    "a": "a4@",
    "b": "b8",
    "c": "c",
    "d": "d",
    "e": "e3",
    "g": "g69",
    "h": "h",
    "i": "i1!|",
    "l": "l1|",
    "m": "m",
    "n": "n",
    "o": "o0",
    "p": "p",
    "r": "r",
    "s": "s5$",
    "t": "t7+",
    "u": "u",
    "x": "x",
    "y": "y",
    "z": "z2",
}

# Up to two separator chars allowed between consecutive letters.
_SEP = r"[\s._\-]{0,2}"
# Boundary: don't match inside a larger alphanumeric/leet token.
_LB = r"(?<![a-z0-9@$+|!])"
_RB = r"(?![a-z0-9@$+|!])"


def _char_class(ch: str) -> str:
    if ch == " ":
        # spaces in multi-word terms become flexible (allow joined / hyphenated)
        return r"[\s._\-]*"
    alts = _LEET.get(ch, re.escape(ch))
    return f"[{alts}]" if len(alts) > 1 else re.escape(alts)


def leet_regex(term: str) -> re.Pattern:
    """Compile a leet- and separator-tolerant pattern for a canonical term."""
    chars = list(term)
    pieces: list[str] = []
    for i, ch in enumerate(chars):
        if i == 0:
            pieces.append(_char_class(ch))
            continue
        # no extra separator around an explicit space-class
        if ch == " " or chars[i - 1] == " ":
            pieces.append(_char_class(ch))
        else:
            pieces.append(_SEP + _char_class(ch))
    return re.compile(_LB + "".join(pieces) + _RB, re.IGNORECASE)


# ── Chemical families (canonical, de-accented, lowercase) ────────────────────
ACID_TERMS = [
    "acid", "acido", "muriatic", "muriatico",
    "hydrochloric", "clorhidrico", "sulfuric", "sulfurico",
]
AMMONIA_TERMS = ["ammonia", "amoniaco"]
CHLORINE_TERMS = [
    "chlorine", "cloro", "bleach", "lejia",
    "hypochlorite", "hipoclorito",
    "trichlor", "dichlor", "tricloro", "dicloro", "cal hypo",
    "calcium hypochlorite", "hipoclorito de calcio", "sodium hypochlorite",
]
# Solid chlorine products that react dangerously when combined with EACH OTHER.
# Used for the "two distinct solid oxidizers" rule (e.g. trichlor + cal hypo).
# English + Spanish spellings map to a shared canonical key.
SOLID_OXIDIZER_TERMS = {
    "trichlor": "trichlor",
    "tricloro": "trichlor",
    "dichlor": "dichlor",
    "dicloro": "dichlor",
    "cal hypo": "calhypo",
    "calcium hypochlorite": "calhypo",
    "hipoclorito de calcio": "calhypo",
}

# Verbs that mean "combine substances" (multilingual). Deliberately excludes
# "add"/"pour" — those are dosing verbs unless two chemicals are named, which
# the family co-occurrence rule already covers.
MIX_VERBS = [
    "mix", "mixing", "combine", "combining", "blend", "blending",
    "mezclar", "mezcla", "combinar", "juntar",
]

# Compiled forms
ACID_PATTERNS = [leet_regex(t) for t in ACID_TERMS]
AMMONIA_PATTERNS = [leet_regex(t) for t in AMMONIA_TERMS]
CHLORINE_PATTERNS = [(t, leet_regex(t)) for t in CHLORINE_TERMS]
SOLID_OXIDIZER_PATTERNS = [(canon, leet_regex(term)) for term, canon in SOLID_OXIDIZER_TERMS.items()]
MIX_VERB_PATTERNS = [leet_regex(v) for v in MIX_VERBS]

# ── Blueprint literal patterns (§5.5) — kept as a documented backstop. ───────
# Applied to de-leeted, normalized text in detect.py.
MIXING_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bmix(ing)?\b.*\b(acid|muriatic|chlorine|bleach|hypochlorite|trichlor|cal[\s-]?hypo)\b",
        r"\b(acid|muriatic)\b.*\b(chlorine|bleach|hypochlorite)\b",
        r"\b(chlorine|bleach)\b.*\b(acid|ammonia|muriatic)\b",
        r"\b(trichlor|cal[\s-]?hypo)\b.*\b(trichlor|cal[\s-]?hypo)\b",
        r"\bcombine\b.*\b(acid|muriatic|chlorine|bleach|trichlor)\b",
    ]
]

# ── Tier-3 physical-risk patterns (applied to de-leeted normalized text) ─────
# burn/smell co-occurrence is matched in BOTH orders ("burning smell" and
# "smell something burning") with \w* so word suffixes (burn -> burning) match.
T3_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bsmell\w*\b[\s\w]{0,20}\bburn\w*",        # "smell something burning"
        r"\bburn\w*\b[\s\w]{0,20}\bsmell\w*",        # "burning smell"
        r"\bsmell\w*\b[\s\w]{0,20}\bgas\b",          # "smell of gas"
        r"\b(smoke|sparks?|gas leak|gas smell|burnt)\b",
        r"\b(shock(ed|ing)?|electrocut(e|ed|ion)?)\b",
        r"\b(olor a quemado|huele a quemado|chispas?|fuga de gas|huele a gas|descarga electrica|calambre)\b",
        r"\b(open|disassemble|rewire|repair|abrir|desarmar)\b.{0,25}\b(heater|gas|electric\w*|panel|wiring|calentador)\b",
        r"\b(chest pain|can.?t breathe|cannot breathe|unconscious|drowning|faint(ing)?)\b",
        r"\b(dolor de pecho|no puedo respirar|inconsciente|ahog\w+)\b",
        r"\bgas\s+(line|valve|burner|pilot|leak)\b",
    ]
]
