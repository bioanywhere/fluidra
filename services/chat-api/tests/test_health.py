"""Integration-ish test for GET /healthz.

In CI without a live DB, the engine connection is mocked.
Against a real local Postgres (make dev), this runs as-is.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from chat_api.main import app


@pytest.mark.asyncio
async def test_healthz_returns_ok_with_db():
    """Endpoint returns 200 {"status": "ok"} when DB is reachable."""
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_conn.execute = AsyncMock()

    with patch("chat_api.main.engine") as mock_engine:
        mock_engine.connect.return_value = mock_conn
        mock_engine.dispose = AsyncMock()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert isinstance(body["latency_ms"], int)


@pytest.mark.asyncio
async def test_healthz_returns_503_when_db_down():
    """Endpoint returns 503 when the DB connection fails."""
    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(side_effect=Exception("connection refused"))
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    with patch("chat_api.main.engine") as mock_engine:
        mock_engine.connect.return_value = mock_conn
        mock_engine.dispose = AsyncMock()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/healthz")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "error"
