"""initial schema

Revision ID: 0001
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None

CATEGORY = ("water", "electricity", "sanitation", "roads", "streetlights", "other")
PRIORITY = ("high", "normal", "low")
STATUS = ("open", "in_progress", "resolved", "rejected")


def _enum(name: str, values: tuple[str, ...]) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in (("complaint_category", CATEGORY), ("complaint_priority", PRIORITY),
                         ("complaint_status", STATUS)):
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("reporter_contact", sa.String(200)),
        sa.Column("category", _enum("complaint_category", CATEGORY), nullable=False),
        sa.Column("priority", _enum("complaint_priority", PRIORITY), nullable=False),
        sa.Column("status", _enum("complaint_status", STATUS), nullable=False,
                  server_default="open"),
        sa.Column("ai_summary", sa.String(140)),
        sa.Column("triaged_by", sa.String(32), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("char_length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_len"),
        sa.CheckConstraint("char_length(location) BETWEEN 3 AND 200",
                           name="ck_complaints_location_len"),
        sa.CheckConstraint("ai_summary IS NULL OR char_length(ai_summary) <= 140",
                           name="ck_complaints_summary_len"),
        sa.CheckConstraint(
            "triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback','simulated')",
            name="ck_complaints_triaged_by"),
    )
    # (status, priority): serves the dashboard filter "WHERE status = ? AND priority = ?"
    # and the stats GROUP BY status / priority.
    op.create_index("ix_complaints_status_priority", "complaints", ["status", "priority"])
    # created_at: serves the list query "ORDER BY created_at DESC LIMIT ? OFFSET ?".
    op.create_index("ix_complaints_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")
    for name in ("complaint_status", "complaint_priority", "complaint_category"):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
