"""
Authentication (LOCAL STUB).

Production verifies a Firebase JWT from the Authorization header (blueprint §2).
For local dev we accept any/no token and return a fixed dev user, so the flow is
exercisable without Firebase. The dependency shape is what the real verifier will
have, so swapping it in is a one-file change.
"""
from __future__ import annotations

from fastapi import Header


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    # TODO(prod): verify Firebase JWT in `authorization` and extract the uid.
    return {"firebase_uid": "dev-user", "locale": "en"}
