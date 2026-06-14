"""
The safety policy is versioned (blueprint §4.1 SAFETY_POLICY_VERSION). Every
decision carries the policy version for audit traceability. A version bump is a
deliberate, reviewed act — this test makes an accidental change visible.
"""
import safety_policy as policy
from safety_gateway.classifier import classify
from safety_gateway.intent import KeywordIntentModel


def test_policy_has_version():
    assert policy.VERSION == "2025.06.0"


def test_decision_carries_policy_version():
    d = classify("how much chlorine do I add", KeywordIntentModel())
    assert d.policy_version == policy.VERSION
