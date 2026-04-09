"""Allow multiple recordings per session and add mime_type column update

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the unique constraint that enforced one recording per session
    op.drop_constraint("session_recordings_session_id_key", "session_recordings", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("session_recordings_session_id_key", "session_recordings", ["session_id"])
