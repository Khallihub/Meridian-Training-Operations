"""Add search_export_jobs table for async export job tracking

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-13

Changes:
- search_export_jobs: new table for async search export job lifecycle
  (queued → processing → completed/failed)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            sa.Enum("queued", "processing", "completed", "failed", name="searchexportjobstatus"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("format", sa.String(10), nullable=False, server_default="csv"),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("caller_role", sa.String(50), nullable=True),
        sa.Column("caller_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_search_export_jobs_status", "search_export_jobs", ["status"])
    op.create_index("idx_search_export_jobs_created_at", "search_export_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_search_export_jobs_created_at", table_name="search_export_jobs")
    op.drop_index("idx_search_export_jobs_status", table_name="search_export_jobs")
    op.drop_table("search_export_jobs")
    op.execute("DROP TYPE IF EXISTS searchexportjobstatus")
