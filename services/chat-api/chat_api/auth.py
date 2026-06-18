"""
Authentication.

`AUTH_MODE` selects the strategy:
- **stub** (default) — accept any/no token and return a fixed dev user. Used by
  local dev and the current hosted demo, so the flow is exercisable without
  Firebase. The dependency shape matches the real verifier, so switching is
  config-only.
- **firebase** — require a Firebase ID token in `Authorization: Bearer <token>`,
  verify it against Google's public certs (audience = `FIREBASE_PROJECT_ID`), and
  return the Firebase uid. Per-user conversation history then keys off that uid.

No new dependency: verification uses `google-auth` (already present via Vertex).
`verify_token` is module-level so tests can swap it without hitting Google.
"""
from __future__ import annotations

from fastapi import Header, HTTPException

from .config import settings

_DEV_USER = {"firebase_uid": "dev-user", "email": None, "locale": "en"}


def _verify_firebase_token(token: str) -> dict:
    # Lazy import so stub mode / tests don't need the transport wired.
    from google.auth.transport import requests as g_requests
    from google.oauth2 import id_token as g_id_token

    return g_id_token.verify_firebase_token(
        token, g_requests.Request(), audience=settings.firebase_project_id or None
    )


# Swappable in tests (monkeypatch chat_api.auth.verify_token).
verify_token = _verify_firebase_token


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if settings.auth_mode != "firebase":
        return dict(_DEV_USER)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = verify_token(token)
    except HTTPException:
        raise
    except Exception as exc:  # invalid / expired / wrong-audience token
        raise HTTPException(status_code=401, detail="invalid token") from exc
    uid = claims.get("user_id") or claims.get("sub") or claims.get("uid")
    if not uid:
        raise HTTPException(status_code=401, detail="token has no uid")
    return {"firebase_uid": uid, "email": claims.get("email"), "locale": "en"}
