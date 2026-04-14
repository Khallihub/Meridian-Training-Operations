"""Align all enum types and values to PRD specification

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-13

Changes:
- SessionStatus: add draft/ended/recording_processing/recording_published/
    closed_no_recording/archived; rename completed→ended, cancelled→canceled
- BookingStatus: rename pending→requested, rescheduled→rescheduled_out,
    cancelled→canceled; add completed
- OrderStatus: rename pending→awaiting_payment, cancelled→canceled,
    needs_review→closed_unpaid; split refunded→refunded_partial+refunded_full;
    add refund_pending
- RefundStatus: rename pending→requested; add pending_review/processing/failed/canceled
- IngestionRunStatus: rename success→succeeded; add queued/partial_failed/canceled/resolved
- IngestionSourceType: rename batch_file→file, cdc_mysql→mysql_cdc, cdc_pg→postgres_cdc
- PromotionType: rename pct_off→percent_off, bogo→bogo_selected_workshops;
    add threshold_fixed_off
"""
from typing import Optional, Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_enum_and_column(
    table: str,
    column: str,
    old_type: str,
    new_values: list,
    renames: dict,
    column_default: Optional[str] = None,
) -> None:
    """
    Rebuild a PostgreSQL enum type and remap existing column values.

    Strategy:
    1. DROP column DEFAULT (if any) — defaults like 'scheduled'::sessionstatus hold
       a reference to the type that survives ALTER COLUMN TYPE and blocks DROP TYPE.
    2. ALTER COLUMN to TEXT so the column itself no longer depends on the enum.
    3. DROP the old enum type.
    4. CREATE the new enum type with the desired values.
    5. UPDATE rows: remap old values to new ones (plain text comparison, no enum cast).
    6. ALTER COLUMN back to the rebuilt enum type.
    7. Restore DEFAULT using the new enum type (if a default was supplied).
    """
    # Step 1: drop the column default so it no longer references the enum type
    if column_default is not None:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")

    # Step 2: detach the column from the enum
    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text USING {column}::text"
    )

    # Step 3: now the type has no dependents — drop it
    op.execute(f"DROP TYPE {old_type}")

    # Step 4: recreate with the full desired value set
    values_sql = ", ".join(f"'{v}'" for v in new_values)
    op.execute(f"CREATE TYPE {old_type} AS ENUM ({values_sql})")

    # Step 5: remap old → new values while the column is still text
    for old_val, new_val in renames.items():
        op.execute(
            f"UPDATE {table} SET {column} = '{new_val}' WHERE {column} = '{old_val}'"
        )

    # Step 6: cast column back to the rebuilt enum type
    op.execute(
        f"ALTER TABLE {table} ALTER COLUMN {column} "
        f"TYPE {old_type} USING {column}::{old_type}"
    )

    # Step 7: restore the column default
    if column_default is not None:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"SET DEFAULT '{column_default}'::{old_type}"
        )


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. SessionStatus  (default: 'scheduled' stays 'scheduled')
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="sessions",
        column="status",
        old_type="sessionstatus",
        new_values=["draft", "scheduled", "live", "ended", "recording_processing",
                    "recording_published", "closed_no_recording", "canceled", "archived"],
        renames={
            "completed": "ended",
            "cancelled": "canceled",
        },
        column_default="scheduled",
    )

    # ------------------------------------------------------------------
    # 2. BookingStatus  (default: 'pending' → 'requested')
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="bookings",
        column="status",
        old_type="bookingstatus",
        new_values=["requested", "confirmed", "rescheduled_out", "canceled", "completed", "no_show"],
        renames={
            "pending": "requested",
            "rescheduled": "rescheduled_out",
            "cancelled": "canceled",
        },
        column_default="requested",
    )

    # ------------------------------------------------------------------
    # 3. OrderStatus  (default: 'pending' → 'awaiting_payment')
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="orders",
        column="status",
        old_type="orderstatus",
        new_values=["awaiting_payment", "paid", "closed_unpaid", "canceled",
                    "refund_pending", "refunded_partial", "refunded_full"],
        renames={
            "pending": "awaiting_payment",
            "cancelled": "canceled",
            "needs_review": "closed_unpaid",
            "refunded": "refunded_full",
        },
        column_default="awaiting_payment",
    )

    # ------------------------------------------------------------------
    # 4. RefundStatus  (default: 'pending' → 'requested')
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="refunds",
        column="status",
        old_type="refundstatus",
        new_values=["requested", "pending_review", "approved", "processing",
                    "completed", "rejected", "failed", "canceled"],
        renames={
            "pending": "requested",
        },
        column_default="requested",
    )

    # ------------------------------------------------------------------
    # 5. IngestionRunStatus  (default: 'running' stays 'running')
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="ingestion_runs",
        column="status",
        old_type="ingestionrunstatus",
        new_values=["queued", "running", "succeeded", "partial_failed", "failed", "canceled", "resolved"],
        renames={
            "success": "succeeded",
        },
        column_default="running",
    )

    # ------------------------------------------------------------------
    # 6. IngestionSourceType  (no column default)
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="ingestion_sources",
        column="type",
        old_type="ingestionsourcetype",
        new_values=["kafka", "flume", "logstash", "file", "mysql_cdc", "postgres_cdc"],
        renames={
            "batch_file": "file",
            "cdc_mysql": "mysql_cdc",
            "cdc_pg": "postgres_cdc",
        },
    )

    # ------------------------------------------------------------------
    # 7. PromotionType  (no column default)
    # ------------------------------------------------------------------
    _rename_enum_and_column(
        table="promotions",
        column="type",
        old_type="promotiontype",
        new_values=["percent_off", "fixed_off", "threshold_fixed_off", "bogo_selected_workshops"],
        renames={
            "pct_off": "percent_off",
            "bogo": "bogo_selected_workshops",
        },
    )


def downgrade() -> None:
    # Reverse SessionStatus  (default: 'scheduled')
    _rename_enum_and_column(
        table="sessions",
        column="status",
        old_type="sessionstatus",
        new_values=["scheduled", "live", "completed", "cancelled"],
        renames={
            "ended": "completed",
            "canceled": "cancelled",
            "draft": "scheduled",
            "recording_processing": "completed",
            "recording_published": "completed",
            "closed_no_recording": "completed",
            "archived": "completed",
        },
        column_default="scheduled",
    )

    # Reverse BookingStatus  (default: 'requested' → 'pending')
    _rename_enum_and_column(
        table="bookings",
        column="status",
        old_type="bookingstatus",
        new_values=["pending", "confirmed", "rescheduled", "cancelled", "no_show"],
        renames={
            "requested": "pending",
            "rescheduled_out": "rescheduled",
            "canceled": "cancelled",
            "completed": "pending",
        },
        column_default="pending",
    )

    # Reverse OrderStatus  (default: 'awaiting_payment' → 'pending')
    _rename_enum_and_column(
        table="orders",
        column="status",
        old_type="orderstatus",
        new_values=["pending", "paid", "cancelled", "refunded", "needs_review"],
        renames={
            "awaiting_payment": "pending",
            "canceled": "cancelled",
            "closed_unpaid": "needs_review",
            "refund_pending": "paid",
            "refunded_partial": "refunded",
            "refunded_full": "refunded",
        },
        column_default="pending",
    )

    # Reverse RefundStatus  (default: 'requested' → 'pending')
    _rename_enum_and_column(
        table="refunds",
        column="status",
        old_type="refundstatus",
        new_values=["pending", "approved", "completed", "rejected"],
        renames={
            "requested": "pending",
            "pending_review": "pending",
            "processing": "approved",
            "failed": "rejected",
            "canceled": "rejected",
        },
        column_default="pending",
    )

    # Reverse IngestionRunStatus  (default: 'running')
    _rename_enum_and_column(
        table="ingestion_runs",
        column="status",
        old_type="ingestionrunstatus",
        new_values=["running", "success", "failed"],
        renames={
            "succeeded": "success",
            "queued": "running",
            "partial_failed": "failed",
            "canceled": "failed",
            "resolved": "success",
        },
        column_default="running",
    )

    # Reverse IngestionSourceType  (no default)
    _rename_enum_and_column(
        table="ingestion_sources",
        column="type",
        old_type="ingestionsourcetype",
        new_values=["kafka", "logstash", "flume", "batch_file", "cdc_mysql", "cdc_pg"],
        renames={
            "file": "batch_file",
            "mysql_cdc": "cdc_mysql",
            "postgres_cdc": "cdc_pg",
        },
    )

    # Reverse PromotionType  (no default)
    _rename_enum_and_column(
        table="promotions",
        column="type",
        old_type="promotiontype",
        new_values=["pct_off", "fixed_off", "bogo"],
        renames={
            "percent_off": "pct_off",
            "bogo_selected_workshops": "bogo",
            "threshold_fixed_off": "fixed_off",
        },
    )
