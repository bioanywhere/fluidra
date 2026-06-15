"""
Deterministic dosing math (blueprint §6).

Pure functions over the validated chemistry-tables constants. No LLM, no I/O.
Every result carries the fixed safety warnings and flags any out-of-range target.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import chemistry_tables as ct


@dataclass
class DoseResult:
    parameter: str            # "free_chlorine" | "alkalinity"
    product: str              # human-readable product label
    grams: float              # amount to add (grams); 0 if none needed
    volume_m3: float
    current_ppm: float
    target_ppm: float
    warnings: list[str] = field(default_factory=list)
    note: str = ""

    def rounded_grams(self) -> int:
        return int(round(self.grams))


def _validate(volume_m3: float, current_ppm: float, target_ppm: float) -> None:
    if volume_m3 <= 0:
        raise ValueError("volume_m3 must be positive")
    if current_ppm < 0 or target_ppm < 0:
        raise ValueError("readings must be non-negative")


def _range_warnings(parameter: str, target_ppm: float) -> list[str]:
    rng = ct.SAFE_RANGES.get(parameter)
    if not rng:
        return []
    if target_ppm < rng["min"] or target_ppm > rng["max"]:
        return [
            f"Target {target_ppm} is outside the recommended {parameter} range "
            f"({rng['min']}–{rng['max']} ppm). Aim for ~{rng['ideal']} ppm."
        ]
    return []


def chlorine_dose(
    volume_m3: float,
    current_ppm: float,
    target_ppm: float,
    product: str = ct.DEFAULT_CHLORINE_PRODUCT,
) -> DoseResult:
    """Grams of a chlorine product to raise free chlorine from current to target."""
    _validate(volume_m3, current_ppm, target_ppm)
    if product not in ct.CHLORINE_PRODUCTS:
        raise ValueError(f"unknown chlorine product {product!r}")
    spec = ct.CHLORINE_PRODUCTS[product]
    f = spec["available_chlorine"]

    delta = target_ppm - current_ppm
    warnings = list(ct.DOSING_SAFETY_WARNINGS) + _range_warnings("free_chlorine", target_ppm)

    if delta <= 0:
        return DoseResult(
            parameter="free_chlorine", product=spec["label"], grams=0.0,
            volume_m3=volume_m3, current_ppm=current_ppm, target_ppm=target_ppm,
            warnings=warnings,
            note="Free chlorine is already at or above the target — no addition needed.",
        )

    grams = delta * volume_m3 / f
    return DoseResult(
        parameter="free_chlorine", product=spec["label"], grams=grams,
        volume_m3=volume_m3, current_ppm=current_ppm, target_ppm=target_ppm,
        warnings=warnings,
        note=f"Add ~{int(round(grams))} g of {spec['label']} to raise free chlorine "
             f"by {delta:g} ppm, then re-test.",
    )


def alkalinity_dose(
    volume_m3: float,
    current_ppm: float,
    target_ppm: float,
) -> DoseResult:
    """Grams of sodium bicarbonate to raise total alkalinity to the target."""
    _validate(volume_m3, current_ppm, target_ppm)
    factor = ct.ALKALINITY["g_per_m3_per_ppm"]
    product = ct.ALKALINITY["raise_product"]

    delta = target_ppm - current_ppm
    warnings = list(ct.DOSING_SAFETY_WARNINGS) + _range_warnings("alkalinity", target_ppm)

    if delta <= 0:
        return DoseResult(
            parameter="alkalinity", product=product, grams=0.0,
            volume_m3=volume_m3, current_ppm=current_ppm, target_ppm=target_ppm,
            warnings=warnings,
            note="Alkalinity is already at or above the target — no addition needed.",
        )

    grams = delta * volume_m3 * factor
    return DoseResult(
        parameter="alkalinity", product=product, grams=grams,
        volume_m3=volume_m3, current_ppm=current_ppm, target_ppm=target_ppm,
        warnings=warnings,
        note=f"Add ~{int(round(grams))} g of {product} to raise total alkalinity "
             f"by {delta:g} ppm, then re-test.",
    )
