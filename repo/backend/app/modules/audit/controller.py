import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.pagination import Page, PageMeta
from app.modules.audit.models import AuditLog
from app.modules.users.models import User

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_username: str | None
    entity_type: str
    entity_id: str
    action: str
    old_value: dict | None
    new_value: dict | None
    ip_address: str | None
    created_at: datetime


@router.get("", response_model=Page[AuditLogOut])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    action: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    _=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    base = select(AuditLog).outerjoin(User, AuditLog.actor_id == User.id)
    if entity_type:
        base = base.where(AuditLog.entity_type == entity_type)
    if entity_id:
        base = base.where(AuditLog.entity_id == entity_id)
    if actor_id:
        base = base.where(AuditLog.actor_id == actor_id)
    if action:
        base = base.where(AuditLog.action == action)
    if from_date:
        base = base.where(AuditLog.created_at >= from_date)
    if to_date:
        base = base.where(AuditLog.created_at <= to_date)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()
    offset = (page - 1) * page_size

    q = (
        select(AuditLog, User.username.label("actor_username"))
        .outerjoin(User, AuditLog.actor_id == User.id)
    )
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if action:
        q = q.where(AuditLog.action == action)
    if from_date:
        q = q.where(AuditLog.created_at >= from_date)
    if to_date:
        q = q.where(AuditLog.created_at <= to_date)

    result = await db.execute(q.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size))
    rows = result.all()

    items = [
        AuditLogOut(
            id=log.id,
            actor_id=log.actor_id,
            actor_username=username,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log, username in rows
    ]

    return Page(
        items=items,
        meta=PageMeta(total_count=total, page=page, page_size=page_size, has_next=(page * page_size < total)),
    )
