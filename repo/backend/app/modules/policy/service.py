from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.modules.policy.models import AdminPolicy
from app.modules.policy.schemas import AdminPolicyResponse, AdminPolicyUpdate

# Defaults used when the table has no row (safety net only; migration seeds one)
_DEFAULTS = AdminPolicyResponse(reschedule_cutoff_hours=2, cancellation_fee_hours=24)


async def get_policy(db: AsyncSession) -> AdminPolicyResponse:
    result = await db.execute(select(AdminPolicy).limit(1))
    policy = result.scalar_one_or_none()
    if not policy:
        return _DEFAULTS
    return AdminPolicyResponse.model_validate(policy)


async def update_policy(db: AsyncSession, payload: AdminPolicyUpdate, actor_id: str) -> AdminPolicyResponse:
    result = await db.execute(select(AdminPolicy).limit(1))
    policy = result.scalar_one_or_none()
    if not policy:
        policy = AdminPolicy()
        db.add(policy)
    old_value = {k: getattr(policy, k, None) for k in payload.model_dump(exclude_none=True)}
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(policy, k, v)
    policy.updated_at = datetime.now(UTC)
    try:
        policy.updated_by = uuid.UUID(actor_id)
    except ValueError:
        pass
    await db.flush()
    await db.refresh(policy)
    await log_audit(
        db, actor_id, "admin_policy", str(policy.id) if hasattr(policy, "id") else "singleton",
        "update", old_value, payload.model_dump(exclude_none=True),
    )
    return AdminPolicyResponse.model_validate(policy)
