from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_roles
from app.modules.policy.schemas import AdminPolicyResponse, AdminPolicyUpdate
from app.modules.policy.service import get_policy, update_policy

router = APIRouter(prefix="/admin/policy", tags=["Admin Policy"])


@router.get("", response_model=AdminPolicyResponse)
async def read_policy(_=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    return await get_policy(db)


@router.patch("", response_model=AdminPolicyResponse)
async def write_policy(
    body: AdminPolicyUpdate,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await update_policy(db, body, str(current_user.id))
