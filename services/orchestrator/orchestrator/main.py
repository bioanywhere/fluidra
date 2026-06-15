"""
FastAPI surface for the orchestrator.

POST /v1/answer runs the RAG graph and returns a grounded, cited answer (or a
graceful escalation). The store/embedder/LLM are built lazily from env on first
use so the service boots even before the vector index or Vertex creds exist.

Env: DATABASE_URL_SYNC, EMBEDDING_BACKEND, LLM_BACKEND, GCP_PROJECT_ID, VERTEX_LOCATION.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel

from observability import init_tracing, setup_logging
from ingestion_worker.embeddings import get_embedder
from ingestion_worker.vectorstore import PgVectorStore

from .graph import answer as run_answer
from .llm import get_llm

setup_logging("orchestrator")
init_tracing("orchestrator")  # exporter chosen by OTEL_TRACES_EXPORTER (no-op locally)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fluidra Pool Assistant — orchestrator", version="0.1.0")

# Lazily-initialised singletons.
_deps: dict = {}


def _get_deps():
    if not _deps:
        embedder = get_embedder()
        dsn = os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql+psycopg2://postgres:localdev@localhost:5432/assistant",
        )
        _deps["embedder"] = embedder
        _deps["store"] = PgVectorStore(dsn=dsn, dim=embedder.dim)
        _deps["llm"] = get_llm()
        logger.info(
            "orchestrator deps ready",
            extra={"embedder": embedder.name, "llm": _deps["llm"].name},
        )
    return _deps


class AnswerRequest(BaseModel):
    query: str
    pool_profile: dict = {}


class CitationOut(BaseModel):
    doc_id: str
    section: str
    brand: str | None = None
    url: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    grounded: bool
    groundedness: float
    escalated: bool


@app.get("/healthz", tags=["ops"])
async def healthz():
    return {"status": "ok"}


@app.post("/v1/answer", response_model=AnswerResponse, tags=["orchestrator"])
async def answer_endpoint(req: AnswerRequest) -> AnswerResponse:
    deps = _get_deps()
    result = run_answer(
        req.query,
        store=deps["store"],
        embedder=deps["embedder"],
        llm=deps["llm"],
        pool_profile=req.pool_profile,
    )
    logger.info(
        "answered",
        extra={
            "grounded": result.grounded,
            "groundedness": round(result.groundedness, 3),
            "escalated": result.escalated,
            "citations": len(result.citations),
        },
    )
    return AnswerResponse(
        answer=result.answer,
        citations=[CitationOut(**c.model_dump()) for c in result.citations],
        grounded=result.grounded,
        groundedness=result.groundedness,
        escalated=result.escalated,
    )
