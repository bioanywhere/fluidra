"""
Conversation persistence (blueprint §1.4, §5.2).

Persists each turn — redacted user message + assistant response, with tier,
intent, latency, cost, citations, the safety event, and any escalation. PII is
already redacted upstream (safety_policy.redact) before anything is stored.

`PersistencePort` is the interface; `DbPersistence` is the Postgres impl. Tests
inject a fake, so the HTTP flow is testable without a database.
"""
from __future__ import annotations

import json
import uuid
from typing import Protocol

from sqlalchemy import text

from .database import async_session_maker
from .pipeline import TurnOutcome


_UUID_NS = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _coerce_uuid(value: str) -> str:
    """Return a valid UUID string. If `value` isn't a UUID (e.g. a client on
    plain HTTP without crypto.randomUUID), map it deterministically so the same
    conversation keeps one id — and the DB CAST never errors."""
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return str(uuid.uuid5(_UUID_NS, str(value)))


class PersistencePort(Protocol):
    async def load_memory(self, conversation_id: str, limit: int) -> list[dict]: ...
    async def record_turn(
        self,
        *,
        conversation_id: str,
        firebase_uid: str,
        user_text_redacted: str,
        outcome: TurnOutcome,
        latency_ms: int,
        cost_usd: float,
    ) -> None: ...


class DbPersistence:
    async def load_memory(self, conversation_id: str, limit: int) -> list[dict]:
        conversation_id = _coerce_uuid(conversation_id)
        async with async_session_maker() as s:
            rows = (
                await s.execute(
                    text(
                        """
                        SELECT role, content_redacted, tier, created_at
                        FROM messages
                        WHERE conversation_id = CAST(:cid AS uuid)
                        ORDER BY created_at DESC
                        LIMIT :n
                        """
                    ),
                    {"cid": conversation_id, "n": limit},
                )
            ).mappings().all()
        return [dict(r) for r in reversed(rows)]

    async def record_turn(
        self,
        *,
        conversation_id: str,
        firebase_uid: str,
        user_text_redacted: str,
        outcome: TurnOutcome,
        latency_ms: int,
        cost_usd: float,
    ) -> None:
        conversation_id = _coerce_uuid(conversation_id)
        async with async_session_maker() as s:
            async with s.begin():
                user_id = (
                    await s.execute(
                        text(
                            """
                            INSERT INTO users (firebase_uid)
                            VALUES (:uid)
                            ON CONFLICT (firebase_uid)
                              DO UPDATE SET firebase_uid = EXCLUDED.firebase_uid
                            RETURNING id
                            """
                        ),
                        {"uid": firebase_uid},
                    )
                ).scalar_one()

                await s.execute(
                    text(
                        """
                        INSERT INTO conversations (id, user_id)
                        VALUES (CAST(:cid AS uuid), :uid)
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {"cid": conversation_id, "uid": user_id},
                )

                user_msg_id = uuid.uuid4()
                await s.execute(
                    text(
                        """
                        INSERT INTO messages
                          (id, conversation_id, role, content_redacted, tier, intent)
                        VALUES
                          (:id, CAST(:cid AS uuid), 'user', :content, :tier, :intent)
                        """
                    ),
                    {
                        "id": user_msg_id, "cid": conversation_id,
                        "content": user_text_redacted, "tier": outcome.tier,
                        "intent": outcome.intent,
                    },
                )

                asst_msg_id = uuid.uuid4()
                await s.execute(
                    text(
                        """
                        INSERT INTO messages
                          (id, conversation_id, role, content_redacted, tier, intent,
                           latency_ms, cost_usd)
                        VALUES
                          (:id, CAST(:cid AS uuid), 'assistant', :content, :tier,
                           :intent, :latency, :cost)
                        """
                    ),
                    {
                        "id": asst_msg_id, "cid": conversation_id,
                        "content": outcome.content, "tier": outcome.tier,
                        "intent": outcome.intent, "latency": latency_ms,
                        "cost": cost_usd,
                    },
                )

                for c in outcome.citations:
                    await s.execute(
                        text(
                            """
                            INSERT INTO citations
                              (message_id, doc_id, section, brand, url)
                            VALUES (:mid, :doc_id, :section, :brand, :url)
                            """
                        ),
                        {
                            "mid": asst_msg_id, "doc_id": c.doc_id,
                            "section": c.section, "brand": c.brand, "url": c.url,
                        },
                    )

                await s.execute(
                    text(
                        """
                        INSERT INTO safety_events
                          (message_id, tier, rule, action, blocked)
                        VALUES (:mid, :tier, :rule, :action, :blocked)
                        """
                    ),
                    {
                        "mid": user_msg_id, "tier": outcome.tier,
                        "rule": outcome.rule or outcome.intent,
                        "action": outcome.type, "blocked": outcome.blocked,
                    },
                )

                if outcome.escalated or outcome.tier == "T3":
                    await s.execute(
                        text(
                            """
                            INSERT INTO escalations
                              (conversation_id, reason, status, context_packet)
                            VALUES (CAST(:cid AS uuid), :reason, 'open',
                                    CAST(:ctx AS jsonb))
                            """
                        ),
                        {
                            "cid": conversation_id,
                            "reason": outcome.rule or "ungrounded",
                            "ctx": json.dumps(
                                {"tier": outcome.tier, "intent": outcome.intent}
                            ),
                        },
                    )


def get_persistence() -> PersistencePort:
    return DbPersistence()
