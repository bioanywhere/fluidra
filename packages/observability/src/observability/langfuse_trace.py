"""
Optional Langfuse integration (blueprint §2, §9.3 — per-trace prompt/response,
cost, eval scores). Entirely env-gated and lazily imported: if Langfuse isn't
configured or installed, every call is a silent no-op, so nothing else depends
on it being present.

Enable by installing the `langfuse` extra and setting LANGFUSE_PUBLIC_KEY /
LANGFUSE_SECRET_KEY / LANGFUSE_HOST.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def record_generation(
    *,
    name: str,
    prompt: str,
    completion: str,
    model: str,
    metadata: dict | None = None,
) -> None:
    """Best-effort record of one LLM generation. No-op unless Langfuse is set up."""
    if not enabled():
        return
    try:
        from langfuse import Langfuse  # lazy

        client = Langfuse(host=os.getenv("LANGFUSE_HOST"))
        client.generation(
            name=name,
            model=model,
            input=prompt,
            output=completion,
            metadata=metadata or {},
        )
    except Exception as exc:  # never let telemetry break a turn
        logger.debug("langfuse record skipped: %s", exc)
