import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pythonjsonlogger.json import JsonFormatter as JsonLogFormatter
from sqlalchemy import text

from .config import settings
from .database import engine


def _setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonLogFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    # keep uvicorn logs going through our formatter
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.access").propagate = True


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    logger.info(
        "chat-api starting",
        extra={"service": "chat-api", "env": settings.env, "port": settings.port},
    )
    yield
    logger.info("chat-api shutting down")
    await engine.dispose()


app = FastAPI(
    title="Fluidra Pool Assistant — chat-api",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz", tags=["ops"])
async def healthz():
    """Liveness + readiness probe: confirms the service is up and Postgres is reachable."""
    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("health check: db unreachable", extra={"error": str(exc)})
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "db": "unreachable"},
        )
    latency_ms = round((time.monotonic() - start) * 1000)
    return {"status": "ok", "db": "ok", "latency_ms": latency_ms}
