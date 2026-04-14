import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.pagination import Page, PageMeta
from app.modules.users.schemas import UserCreate, UserDetailResponse, UserResponse, UserUnmaskResponse, UserUpdate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserDetailResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    role: str | None = None,
    is_active: bool | None = None,
    _=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    items, total = await svc.list(page, page_size, role, is_active)
    return Page(items=items, meta=PageMeta(total_count=total, page=page, page_size=page_size, has_next=(page * page_size < total)))


@router.post("", response_model=UserDetailResponse, status_code=201)
async def create_user(
    body: UserCreate,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await UserService(db).create(body, actor_id=str(current_user.id))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await UserService(db).get(str(current_user.id), admin=False)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.exceptions import ForbiddenError
    is_admin = current_user.role == "admin"
    is_self = str(current_user.id) == str(user_id)
    if not is_admin and not is_self:
        raise ForbiddenError("You can only view your own profile.")
    return await UserService(db).get(str(user_id), admin=is_admin)


@router.patch("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await UserService(db).update(str(user_id), body, actor_id=str(current_user.id))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    await UserService(db).delete(str(user_id), actor_id=str(current_user.id))


@router.post("/{user_id}/unmask", response_model=UserUnmaskResponse)
async def unmask_user_pii(
    user_id: uuid.UUID,
    reason: str = Query(..., min_length=5, description="Business reason for accessing unmasked PII (min 5 chars)."),
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Return unmasked email and phone for a user.

    Admin-only.  Every call is recorded in the audit log with the supplied
    reason regardless of whether the target user exists.
    """
    return await UserService(db).unmask(str(user_id), actor_id=str(current_user.id), reason=reason)
