"""
Detection logic for the two deterministic hard paths: chemical mixing (block)
and physical risk (escalate).

SAFETY-CRITICAL. These functions run BEFORE any LLM call. They are pure,
side-effect-free, and deterministic — no model, no network, no prompt that
could be injected. Returns are intentionally conservative: when in doubt on the
mixing path, block.
"""
from . import patterns as P
from .normalize import normalize, deleet_basic


def _families_present(norm: str) -> dict:
    """Detect which chemical families appear in already-normalized text."""
    acid = any(p.search(norm) for p in P.ACID_PATTERNS)
    ammonia = any(p.search(norm) for p in P.AMMONIA_PATTERNS)
    chlorine_names = {name for name, p in P.CHLORINE_PATTERNS if p.search(norm)}
    solid_oxidizers = {canon for canon, p in P.SOLID_OXIDIZER_PATTERNS if p.search(norm)}
    verb = any(p.search(norm) for p in P.MIX_VERB_PATTERNS)
    return {
        "acid": acid,
        "ammonia": ammonia,
        "chlorine": bool(chlorine_names),
        "solid_oxidizers": solid_oxidizers,
        "verb": verb,
    }


def detect_chemical_mixing(text: str) -> bool:
    """
    True if the text is asking to mix/combine incompatible pool chemicals.

    Multiple independent detectors — a request must evade ALL of them to slip
    through, which is what makes the hard gate robust:
      1. Cross-family co-occurrence: acid+chlorine, chlorine+ammonia, acid+ammonia.
      2. Two distinct solid oxidizers (e.g. trichlor + cal hypo).
      3. A mixing verb co-occurring with any chemical (catches single-family
         requests like "can I mix in some trichlor").
      4. Blueprint literal patterns on a de-leeted copy (documented backstop).
    """
    norm = normalize(text)
    f = _families_present(norm)

    # 1) the canonical lethal combinations
    if (f["acid"] and f["chlorine"]) or (f["chlorine"] and f["ammonia"]) or (f["acid"] and f["ammonia"]):
        return True

    # 2) two distinct solid oxidizers react with each other
    if len(f["solid_oxidizers"]) >= 2:
        return True

    # 3) explicit mixing verb + any chemical present
    if f["verb"] and (f["acid"] or f["ammonia"] or f["chlorine"]):
        return True

    # 4) backstop: blueprint literal patterns over a de-leeted copy
    deleeted = deleet_basic(norm)
    if any(p.search(deleeted) for p in P.MIXING_PATTERNS):
        return True

    return False


def detect_physical_risk(text: str) -> bool:
    """True if the text signals a physical-safety risk that must escalate to a human."""
    candidate = deleet_basic(normalize(text))
    return any(p.search(candidate) for p in P.T3_PATTERNS)
