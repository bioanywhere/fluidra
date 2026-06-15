"""
chemistry-tables — validated pool-chemistry dosing constants and safe ranges.

THIS PACKAGE IS SAFETY-CRITICAL.
All values come from established pool-chemistry references and are intended to be
verified under chemistry review before production. Changes require chemistry
review. Dosing math NEVER comes from an LLM — only from these tables.

Units are metric (the EMEA pilot market): volume in m³, concentrations in ppm
(= mg/L = g/m³). The fundamental relationship used throughout:

    1 ppm increase in 1 m³ of water  ==  1 gram of *pure* (100%) active product

so for a product that is fraction `f` active, grams = ppm * volume_m3 / f.
"""

# ── Safe operating ranges (ppm unless noted) ────────────────────────────────
SAFE_RANGES = {
    "free_chlorine": {"min": 1.0, "max": 3.0, "ideal": 2.0},
    "ph":            {"min": 7.2, "max": 7.6, "ideal": 7.4},   # unitless
    "alkalinity":    {"min": 80,  "max": 120, "ideal": 100},
    "calcium":       {"min": 200, "max": 400, "ideal": 300},
    "cyanuric_acid": {"min": 30,  "max": 50,  "ideal": 40},
    "salt":          {"min": 2700, "max": 3400, "ideal": 3200},
}

# ── Chlorine products: fraction of available chlorine by weight ──────────────
# Representative label values; verify against the specific product under review.
CHLORINE_PRODUCTS = {
    "cal_hypo":   {"available_chlorine": 0.65, "label": "Calcium hypochlorite (65%)"},
    "dichlor":    {"available_chlorine": 0.56, "label": "Dichlor (56%)"},
    "trichlor":   {"available_chlorine": 0.90, "label": "Trichlor (90%)"},
    "liquid_12":  {"available_chlorine": 0.125, "label": "Liquid chlorine (12.5%)"},
}
DEFAULT_CHLORINE_PRODUCT = "cal_hypo"

# ── Total-alkalinity adjustment ─────────────────────────────────────────────
# Sodium bicarbonate (baking soda) to RAISE total alkalinity.
# ~1.7 g/m³ raises TA by ~1 ppm (≈1.5 lb per 10,000 gal per 10 ppm).
ALKALINITY = {
    "raise_product": "sodium bicarbonate",
    "g_per_m3_per_ppm": 1.7,
}

# Fixed safety warnings attached to every dosing recommendation.
DOSING_SAFETY_WARNINGS = [
    "Never mix pool chemicals together — add each one separately to the water.",
    "Add chemicals to water (not water to chemicals), with the pump running.",
    "Re-test the water after about 4 hours before swimming.",
]
