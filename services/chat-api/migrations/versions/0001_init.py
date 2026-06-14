"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("firebase_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("locale", sa.String(10), nullable=False, server_default="en"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "pool_profiles",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pool_type", sa.String(40)),
        sa.Column("volume_m3", sa.Numeric(8, 2)),
        sa.Column("equipment", JSONB, server_default="[]"),
        sa.Column("sanitizer", sa.String(40)),
    )

    op.create_table(
        "conversations",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", sa.String(40), server_default="app"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "messages",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),  # user | assistant | system
        sa.Column("content_redacted", sa.Text, nullable=False),
        sa.Column("tier", sa.String(8)),    # T1 | T2 | T3
        sa.Column("intent", sa.String(64)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_messages_conversation",
        "messages",
        ["conversation_id", "created_at"],
    )

    op.create_table(
        "citations",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "message_id",
            UUID,
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("doc_id", sa.String(64)),
        sa.Column("section", sa.String(128)),
        sa.Column("brand", sa.String(40)),
        sa.Column("url", sa.Text),
    )

    op.create_table(
        "safety_events",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "message_id",
            UUID,
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
        ),
        sa.Column("tier", sa.String(8)),
        sa.Column("rule", sa.String(80)),
        sa.Column("action", sa.String(40)),
        sa.Column("blocked", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "escalations",
        sa.Column(
            "id",
            UUID,
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
        ),
        sa.Column("reason", sa.String(80)),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("context_packet", JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    for t in [
        "escalations",
        "safety_events",
        "citations",
        "messages",
        "conversations",
        "pool_profiles",
        "users",
    ]:
        op.drop_table(t)
