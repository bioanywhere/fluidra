"""
shared-types — Pydantic models shared across all Fluidra Pool Assistant services.

These are the canonical request/response shapes. Services import from here;
the API contract cannot drift between services.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class Tier(str, Enum):
    T1 = "T1"   # informational — answer with citations
    T2 = "T2"   # chemistry/dosing — structured flow
    T3 = "T3"   # physical risk — escalate to human


class ResponseType(str, Enum):
    ANSWER = "answer"
    DOSING_PROMPT = "dosing_prompt"
    ESCALATION = "escalation"


class Citation(BaseModel):
    doc_id: str
    section: str
    brand: Optional[str] = None
    url: Optional[str] = None


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    tier: Tier
    type: ResponseType
    content: str
    citations: list[Citation] = []
    warnings: list[str] = []
