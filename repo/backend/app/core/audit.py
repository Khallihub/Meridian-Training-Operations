"""Audit log helpers. All sensitive state-change operations call log_audit."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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
    """Insert an audit_log row. Intentionally fire-and-forget (no raise)."""
    from app.modules.audit.models import AuditLog  # late import to avoid circular

    try:
        if isinstance(actor_id, str):
            try:
                actor_uuid = uuid.UUID(actor_id)
            except ValueError:
                actor_uuid = None  # non-UUID callers like "system" are stored as NULL
        else:
            actor_uuid = actor_id
        stmt = insert(AuditLog).values(
            id=uuid.uuid4(),
            actor_id=actor_uuid,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
        )
        await db.execute(stmt)
    except Exception as exc:
        # Audit failure must never break business flow, but must be observable
        logger.error(
            "audit_log_failed actor=%s entity=%s/%s action=%s error=%r",
            actor_id, entity_type, entity_id, action, exc,
        )
