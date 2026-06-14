"""
FastAPI surface for the safety gateway.

In the MVP the gateway is an in-process module imported by chat-api, but it is
also exposed as a standalone service (per blueprint §1.3 Target state) so it can
be deployed and A/B-tested independently. Booting it here also keeps `make dev`
green for the whole stack.
"""
import logging
import sys

from fastapi import FastAPI
from pydantic import BaseModel
from pythonjsonlogger.json import JsonFormatter

import safety_policy as policy

from .classifier import Decision, classify
from .intent import KeywordIntentModel

_intent_model = KeywordIntentModel()


def _setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel("INFO")


_setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Fluidra Pool Assistant — safety-gateway", version="0.1.0")


class ClassifyRequest(BaseModel):
    message: str


class ClassifyResponse(BaseModel):
    tier: str
    intent: str
    blocked: bool
    rule: str | None
    policy_version: str
    # NOTE: redacted_text is intentionally NOT returned over the wire; it is
    # for internal persistence only.


@app.get("/healthz", tags=["ops"])
async def healthz():
    return {"status": "ok", "policy_version": policy.VERSION}


@app.post("/v1/classify", response_model=ClassifyResponse, tags=["safety"])
async def classify_endpoint(req: ClassifyRequest) -> ClassifyResponse:
    decision: Decision = classify(req.message, _intent_model)
    logger.info(
        "classified",
        extra={
            "tier": decision.tier.value,
            "intent": decision.intent,
            "blocked": decision.blocked,
            "rule": decision.rule,
            "policy_version": decision.policy_version,
        },
    )
    return ClassifyResponse(
        tier=decision.tier.value,
        intent=decision.intent,
        blocked=decision.blocked,
        rule=decision.rule,
        policy_version=decision.policy_version,
    )
