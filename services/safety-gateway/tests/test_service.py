"""Service-level tests for the safety-gateway FastAPI surface."""
from fastapi.testclient import TestClient

from safety_gateway.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["policy_version"] == "2025.06.0"


def test_classify_blocks_mixing():
    r = client.post("/v1/classify", json={"message": "can I mix acid and chlorine"})
    assert r.status_code == 200
    body = r.json()
    assert body["blocked"] is True
    assert body["rule"] == "mixing_block"
    assert body["tier"] == "T2"


def test_classify_escalates_physical_risk():
    r = client.post("/v1/classify", json={"message": "burning smell from the heater"})
    body = r.json()
    assert body["tier"] == "T3"
    assert body["rule"] == "escalate"


def test_classify_routes_fault_code_to_t1():
    r = client.post("/v1/classify", json={"message": "my system shows code 125"})
    body = r.json()
    assert body["tier"] == "T1"
    assert body["blocked"] is False


def test_classify_does_not_leak_redacted_text():
    """The wire response must not echo back internal redacted_text."""
    r = client.post("/v1/classify", json={"message": "email me at a@b.com"})
    assert "redacted_text" not in r.json()
