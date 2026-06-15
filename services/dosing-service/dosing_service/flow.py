"""
Dosing flow (blueprint §1.4, §7.4).

A dosing turn never produces a free-text number from an LLM. This builds the
structured "dosing card": if the message already contains the pool volume and
the current/target reading, it computes the dose deterministically; otherwise it
asks for the missing inputs. Either way the response is a card, not prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import chemistry_tables as ct

from .calculator import DoseResult, alkalinity_dose, chlorine_dose


@dataclass
class DosingCard:
    parameter: str
    content: str
    warnings: list[str] = field(default_factory=list)
    needs: list[str] = field(default_factory=list)   # inputs still required
    result: DoseResult | None = None


_VOLUME_M3 = re.compile(r"(\d+(?:\.\d+)?)\s*(?:m3|m³|cubic\s*met(?:er|re)s?)", re.I)
_VOLUME_L = re.compile(r"(\d+(?:\.\d+)?)\s*(?:l|lt|liters?|litres?)\b", re.I)
_CURRENT = re.compile(r"(?:current|now|at|from)\s*(?:is\s*)?(\d+(?:\.\d+)?)\s*ppm", re.I)
_TARGET = re.compile(r"(?:target|to|want|reach|raise to)\s*(\d+(?:\.\d+)?)\s*ppm", re.I)
_ANY_PPM = re.compile(r"(\d+(?:\.\d+)?)\s*ppm", re.I)


def _parse_volume_m3(text: str) -> float | None:
    m = _VOLUME_M3.search(text)
    if m:
        return float(m.group(1))
    m = _VOLUME_L.search(text)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def _detect_parameter(text: str) -> str:
    t = text.lower()
    if "alkalin" in t:
        return "alkalinity"
    return "free_chlorine"  # default to the most common dosing question


def build_dosing_card(message: str) -> DosingCard:
    """Interpret a Tier-2 dosing message into a computed or input-requesting card."""
    parameter = _detect_parameter(message)
    label = "chlorine" if parameter == "free_chlorine" else "alkalinity"

    volume_m3 = _parse_volume_m3(message)
    current = _CURRENT.search(message)
    target = _TARGET.search(message)

    # Fallbacks: if exactly two ppm values are present, treat as current, target.
    ppms = [float(x) for x in _ANY_PPM.findall(message)]
    current_ppm = float(current.group(1)) if current else (ppms[0] if len(ppms) >= 2 else None)
    target_ppm = float(target.group(1)) if target else (ppms[1] if len(ppms) >= 2 else None)
    if target_ppm is None:
        target_ppm = ct.SAFE_RANGES[parameter]["ideal"]  # sensible default target

    needs = []
    if volume_m3 is None:
        needs.append("pool volume (e.g. 50 m³ or 50000 L)")
    if current_ppm is None:
        needs.append(f"current {label} reading (ppm)")

    if needs:
        return DosingCard(
            parameter=parameter,
            content=(
                f"To calculate your {label} dose I need: " + "; ".join(needs) +
                f". Target is ~{target_ppm:g} ppm (the recommended midpoint)."
            ),
            warnings=list(ct.DOSING_SAFETY_WARNINGS),
            needs=needs,
        )

    if parameter == "alkalinity":
        result = alkalinity_dose(volume_m3, current_ppm, target_ppm)
    else:
        result = chlorine_dose(volume_m3, current_ppm, target_ppm)

    return DosingCard(
        parameter=parameter,
        content=result.note,
        warnings=result.warnings,
        result=result,
    )
