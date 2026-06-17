"""Admin corpus API — the token gate fails closed (these paths need no DB)."""
import pytest
from fastapi.testclient import TestClient

from chat_api.config import settings
from chat_api.main import app


@pytest.fixture(autouse=True)
def _reset_token(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.setattr(settings, "admin_token", "")  # admin disabled by default
    yield


def test_admin_disabled_returns_503_when_no_token():
    c = TestClient(app)
    assert c.get("/v1/admin/documents").status_code == 503


def test_missing_or_wrong_token_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "s3cret")
    c = TestClient(app)
    assert c.get("/v1/admin/documents").status_code == 401
    assert c.get("/v1/admin/documents", headers={"X-Admin-Token": "nope"}).status_code == 401
    # delete + upload are guarded the same way (no DB touched on the 401 path)
    assert c.delete("/v1/admin/documents/H0567500").status_code == 401


def test_token_via_env_is_honored(monkeypatch):
    # settings.admin_token empty -> falls back to the ADMIN_TOKEN env var
    monkeypatch.setenv("ADMIN_TOKEN", "envtok")
    c = TestClient(app)
    assert c.get("/v1/admin/documents", headers={"X-Admin-Token": "wrong"}).status_code == 401
