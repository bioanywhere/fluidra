"""Dosing flow: compute when inputs are present, else request them."""
from dosing_service.flow import build_dosing_card


def test_card_requests_inputs_when_missing():
    card = build_dosing_card("how much chlorine should I add")
    assert card.result is None
    assert card.needs  # asks for volume + current reading
    assert "volume" in card.content.lower()


def test_card_computes_when_inputs_present():
    card = build_dosing_card(
        "my pool is 50 m3, current chlorine is 0 ppm, target 2 ppm, how much do I add"
    )
    assert card.result is not None
    assert card.result.grams > 0
    assert "g of" in card.content.lower()
    assert any("never mix" in w.lower() for w in card.warnings)


def test_card_handles_liters():
    card = build_dosing_card("50000 L pool, chlorine at 1 ppm target 3 ppm")
    assert card.result is not None
    assert card.result.volume_m3 == 50.0


def test_alkalinity_routing():
    card = build_dosing_card("raise alkalinity, 50 m3, current 60 ppm to 100 ppm")
    assert card.parameter == "alkalinity"
    assert card.result is not None
