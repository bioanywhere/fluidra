import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from pythonjsonlogger.json import JsonFormatter as JsonLogFormatter
from sqlalchemy import text

from shared_types import ChatRequest, ChatResponse
from safety_gateway.intent import KeywordIntentModel
from safety_policy import redact

from .auth import get_current_user
from .config import settings
from .database import engine
from .persistence import get_persistence, PersistencePort
from .pipeline import handle_turn
from .rag import get_rag

_intent_model = KeywordIntentModel()


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


@app.post("/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    rag=Depends(get_rag),
    persistence: PersistencePort = Depends(get_persistence),
) -> ChatResponse:
    """The single endpoint clients call (blueprint §5.4). Safety is enforced
    before generation; the turn is persisted (redacted) with tier/latency/cost."""
    start = time.monotonic()
    store, embedder, llm = rag

    # Memory window (loaded per blueprint §1.4; available for future prompt use).
    await persistence.load_memory(req.conversation_id, settings.max_turns_memory)

    outcome = handle_turn(
        req.message, store=store, embedder=embedder, llm=llm, intent_model=_intent_model
    )
    latency_ms = round((time.monotonic() - start) * 1000)
    cost_usd = 0.0  # deterministic/fake paths cost nothing; real Gemini wired later

    await persistence.record_turn(
        conversation_id=req.conversation_id,
        firebase_uid=user["firebase_uid"],
        user_text_redacted=redact(req.message),
        outcome=outcome,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )

    logger.info(
        "chat turn",
        extra={
            "tier": outcome.tier, "type": outcome.type, "intent": outcome.intent,
            "blocked": outcome.blocked, "escalated": outcome.escalated,
            "latency_ms": latency_ms,
        },
    )

    return ChatResponse(
        tier=outcome.tier,
        type=outcome.type,
        content=outcome.content,
        citations=outcome.citations,
        warnings=outcome.warnings,
    )
