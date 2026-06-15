"""Guard the safety-critical constants against accidental edits."""
import chemistry_tables as ct


def test_safe_ranges_are_ordered():
    for name, r in ct.SAFE_RANGES.items():
        assert r["min"] < r["ideal"] < r["max"], f"{name} range not ordered"


def test_chlorine_products_fractions_valid():
    for name, p in ct.CHLORINE_PRODUCTS.items():
        assert 0 < p["available_chlorine"] <= 1.0, name


def test_default_product_exists():
    assert ct.DEFAULT_CHLORINE_PRODUCT in ct.CHLORINE_PRODUCTS


def test_alkalinity_factor_positive():
    assert ct.ALKALINITY["g_per_m3_per_ppm"] > 0
