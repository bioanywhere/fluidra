"""End-user auth: stub vs firebase verification (no Google calls in tests)."""
import pytest
from fastapi import HTTPException

from chat_api import auth
from chat_api.config import settings


def _boom(_token):
    raise ValueError("bad token")


async def test_stub_mode_returns_dev_user(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "stub")
    user = await auth.get_current_user(authorization=None)
    assert user["firebase_uid"] == "dev-user"


async def test_firebase_mode_requires_bearer(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "firebase")
    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(authorization=None)
    assert e.value.status_code == 401


async def test_firebase_mode_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "firebase")
    monkeypatch.setattr(auth, "verify_token", _boom)
    with pytest.raises(HTTPException) as e:
        await auth.get_current_user(authorization="Bearer xyz")
    assert e.value.status_code == 401


async def test_firebase_mode_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(settings, "auth_mode", "firebase")
    monkeypatch.setattr(auth, "verify_token", lambda _t: {"user_id": "abc123", "email": "a@b.com"})
    user = await auth.get_current_user(authorization="Bearer good")
    assert user["firebase_uid"] == "abc123"
    assert user["email"] == "a@b.com"
