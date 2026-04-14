"""Audit log helpers. All sensitive state-change operations call log_audit."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _compute_entry_hash(
    row_id: uuid.UUID,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    action: str,
    old_value: dict | None,
    new_value: dict | None,
    ip_address: str | None,
    created_at: datetime,
    prev_hash: str | None,
) -> str:
    """Return a SHA-256 hex digest over all row fields + prev_hash.

    Fields are serialised deterministically so the hash is stable across
    languages and runtimes.  Null fields are represented as the string "null".
    """
    canonical = "|".join([
        str(row_id),
        str(actor_id) if actor_id is not None else "null",
        entity_type,
        entity_id,
        action,
        json.dumps(old_value, sort_keys=True, default=str) if old_value is not None else "null",
        json.dumps(new_value, sort_keys=True, default=str) if new_value is not None else "null",
        str(ip_address) if ip_address is not None else "null",
        created_at.isoformat(),
        str(prev_hash) if prev_hash is not None else "null",
    ])
    return hashlib.sha256(canonical.encode()).hexdigest()


async def log_audit(
    db: AsyncSession,
    actor_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Insert an audit_log row with tamper-evident hash chain.

    Intentionally fire-and-forget (no raise) so audit failures never interrupt
    business flow, but are always logged as errors.
    """
    from app.modules.audit.models import AuditLog  # late import to avoid circular

    try:
        if isinstance(actor_id, str):
            try:
                actor_uuid = uuid.UUID(actor_id)
            except ValueError:
                actor_uuid = None  # non-UUID callers like "system" are stored as NULL
        else:
            actor_uuid = actor_id

        # Acquire a transaction-scoped PostgreSQL advisory lock so that the
        # "read prev_hash → compute entry_hash → insert" sequence is atomic
        # across concurrent callers within the same DB instance.  The lock is
        # released automatically when the surrounding transaction commits or
        # rolls back, so it never leaks.  The constant 7831642 is an arbitrary
        # key reserved for the audit chain write path.
        from sqlalchemy import text as _text
        await db.execute(_text("SELECT pg_advisory_xact_lock(7831642)"))

        # Now read the chain tip while holding the lock — no other audit insert
        # can interleave between this read and the insert below.
        last_result = await db.execute(
            select(AuditLog.entry_hash)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(1)
        )
        prev_hash: str | None = last_result.scalar_one_or_none()

        row_id = uuid.uuid4()
        created_at = datetime.now(UTC)

        entry_hash = _compute_entry_hash(
            row_id=row_id,
            actor_id=str(actor_uuid) if actor_uuid else None,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            created_at=created_at,
            prev_hash=prev_hash,
        )

        from sqlalchemy import insert
        stmt = insert(AuditLog).values(
            id=row_id,
            actor_id=actor_uuid,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            created_at=created_at,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        await db.execute(stmt)
    except Exception as exc:
        # Audit failure must never break business flow, but must be observable
        logger.error(
            "audit_log_failed actor=%s entity=%s/%s action=%s error=%r",
            actor_id, entity_type, entity_id, action, exc,
        )
