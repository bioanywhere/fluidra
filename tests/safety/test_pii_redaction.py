"""
PII redaction runs upstream of all persistence and the LLM (blueprint §9.2).
The Decision.redacted_text must never contain raw emails or phone numbers.
"""
import pytest

from safety_gateway.classifier import classify

PII_CASES = [
    ("email me at john.doe@example.com about my pump", "[email]", "john.doe@example.com"),
    ("call me on +34 612 345 678 tomorrow", "[phone]", "612 345 678"),
    ("reach me: jane_smith@fluidra.co.uk", "[email]", "jane_smith@fluidra.co.uk"),
]


@pytest.mark.parametrize("text,placeholder,raw", PII_CASES)
def test_pii_is_redacted(text, placeholder, raw, intent_model):
    d = classify(text, intent_model)
    assert placeholder in d.redacted_text
    assert raw not in d.redacted_text


def test_redaction_preserves_non_pii_content(intent_model):
    d = classify("my heater shows code 125, email me at x@y.com", intent_model)
    assert "code 125" in d.redacted_text
    assert "[email]" in d.redacted_text
    assert "x@y.com" not in d.redacted_text
