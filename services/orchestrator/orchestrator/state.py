"""Graph state + the orchestrator's result type."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from shared_types import Citation

from ingestion_worker.types import Chunk


class TurnState(TypedDict):
    query: str
    pool_profile: dict
    chunks: list[Chunk]
    answer: str
    citations: list[Citation]
    grounded: bool
    groundedness: float
    escalated: bool


@dataclass
class OrchestratorResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    grounded: bool = False
    groundedness: float = 0.0
    escalated: bool = False
