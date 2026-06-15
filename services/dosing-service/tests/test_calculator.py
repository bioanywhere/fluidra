"""Deterministic dosing math — exact, validated against the documented formula."""
import pytest

from dosing_service.calculator import chlorine_dose, alkalinity_dose


def test_chlorine_dose_basic():
    # 50 m³, raise FC 0 -> 2 ppm with cal hypo (65%): 2*50/0.65 = 153.85 g
    r = chlorine_dose(volume_m3=50, current_ppm=0, target_ppm=2, product="cal_hypo")
    assert r.grams == pytest.approx(153.846, rel=1e-3)
    assert r.parameter == "free_chlorine"
    assert any("Never mix" in w for w in r.warnings)


def test_chlorine_dose_product_scaling():
    # trichlor (90%) needs less than cal hypo (65%) for the same effect
    cal = chlorine_dose(50, 0, 2, product="cal_hypo").grams
    tri = chlorine_dose(50, 0, 2, product="trichlor").grams
    assert tri < cal


def test_chlorine_no_dose_when_at_target():
    r = chlorine_dose(50, 3, 2)
    assert r.grams == 0.0
    assert "no addition" in r.note.lower()


def test_chlorine_out_of_range_target_warns():
    r = chlorine_dose(50, 0, 10)  # 10 ppm is above safe max
    assert any("outside the recommended" in w for w in r.warnings)


def test_alkalinity_dose_basic():
    # 50 m³, 60 -> 100 ppm, 1.7 g/m³/ppm: 40*50*1.7 = 3400 g
    r = alkalinity_dose(volume_m3=50, current_ppm=60, target_ppm=100)
    assert r.grams == pytest.approx(3400.0, rel=1e-6)


def test_invalid_volume_raises():
    with pytest.raises(ValueError):
        chlorine_dose(0, 0, 2)
