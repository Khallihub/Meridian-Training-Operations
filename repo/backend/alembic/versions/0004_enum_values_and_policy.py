"""Add flume/needs_review enum values and admin_policies table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add flume to ingestionsourcetype enum
    op.execute("ALTER TYPE ingestionsourcetype ADD VALUE IF NOT EXISTS 'flume'")

    # Add needs_review to orderstatus enum
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'needs_review'")

    # Create admin_policies table (singleton — one row, seeded below)
    op.create_table(
        "admin_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("reschedule_cutoff_hours", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("cancellation_fee_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    # Seed the single default row so reads always find a row
    op.execute(
        "INSERT INTO admin_policies (reschedule_cutoff_hours, cancellation_fee_hours) VALUES (2, 24)"
    )


def downgrade() -> None:
    op.drop_table("admin_policies")
    # PostgreSQL does not support removing enum values; no-op for enum rollback
