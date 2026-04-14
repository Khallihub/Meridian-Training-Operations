"""Security hardening: external_event_id, promotion priority, audit hash chain

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-13

Changes:
- payments: add external_event_id (unique, nullable) for durable callback idempotency
- promotions: add priority column (integer, default 0) for deterministic tie-break
- audit_logs: add prev_hash and entry_hash columns for tamper-evidence chain
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- payments: durable idempotency key from the gateway ---
    op.add_column(
        "payments",
        sa.Column("external_event_id", sa.String(200), nullable=True),
    )
    op.create_index("idx_payments_external_event_id", "payments", ["external_event_id"])
    op.create_unique_constraint(
        "uq_payments_external_event_id", "payments", ["external_event_id"]
    )

    # --- promotions: deterministic tie-break ordering ---
    op.add_column(
        "promotions",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("idx_promotions_priority", "promotions", ["priority"])

    # --- audit_logs: tamper-evident hash chain ---
    op.add_column(
        "audit_logs",
        sa.Column("prev_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("entry_hash", sa.String(64), nullable=True),
    )
    op.create_index("idx_audit_entry_hash", "audit_logs", ["entry_hash"])

    # Backfill: existing rows receive NULL hashes (chain starts from first new row).
    # A one-time backfill job can be run offline to retroactively hash old rows if
    # required; see ASSUMPTIONS.md for details.


def downgrade() -> None:
    op.drop_index("idx_audit_entry_hash", table_name="audit_logs")
    op.drop_column("audit_logs", "entry_hash")
    op.drop_column("audit_logs", "prev_hash")

    op.drop_index("idx_promotions_priority", table_name="promotions")
    op.drop_column("promotions", "priority")

    op.drop_constraint("uq_payments_external_event_id", "payments", type_="unique")
    op.drop_index("idx_payments_external_event_id", table_name="payments")
    op.drop_column("payments", "external_event_id")
