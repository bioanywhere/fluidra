"""dosing-service — deterministic chemistry dosing (blueprint §6). Never an LLM."""
from .calculator import DoseResult, chlorine_dose, alkalinity_dose
from .flow import DosingCard, build_dosing_card

__all__ = [
    "DoseResult",
    "chlorine_dose",
    "alkalinity_dose",
    "DosingCard",
    "build_dosing_card",
]
