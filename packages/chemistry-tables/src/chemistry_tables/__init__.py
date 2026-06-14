"""
chemistry-tables — validated pool-chemistry dosing tables and safe ranges.

THIS PACKAGE IS SAFETY-CRITICAL.
All values come from Fluidra-approved chemistry references.
Changes require chemistry review. Never replace table lookups with LLM output.
"""

# ── Safe operating ranges ─────────────────────────────────────────────────────
SAFE_RANGES = {
    "ph":            {"min": 7.2, "max": 7.6, "ideal": 7.4},
    "free_chlorine": {"min": 1.0, "max": 3.0, "ideal": 2.0},   # ppm
    "alkalinity":    {"min": 80,  "max": 120,  "ideal": 100},   # ppm as CaCO3
    "calcium":       {"min": 200, "max": 400,  "ideal": 300},   # ppm
    "cyanuric_acid": {"min": 30,  "max": 50,   "ideal": 40},    # ppm (stabilised pools)
    "salt":          {"min": 2700,"max": 3400,  "ideal": 3200},  # ppm (salt-water pools)
}

# ── Placeholder for dosing tables (populated in Milestone 5) ─────────────────
# Structure: parameter → {units, dose_per_10k_litres_per_unit_correction}
# Values will be filled in from Fluidra-approved chemistry tables.
DOSING_TABLES: dict = {}
