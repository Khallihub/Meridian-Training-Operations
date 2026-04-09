from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def update_login_failure(
        self, user_id: uuid.UUID, attempts: int, lock_until: datetime | None
    ) -> None:
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=attempts, locked_until=lock_until)
        )

    async def update_login_success(self, user_id: uuid.UUID) -> None:
        from datetime import UTC
        await self._db.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=0, locked_until=None, last_login=datetime.now(UTC))
        )

    async def update_password(self, user_id: uuid.UUID, new_hash: str) -> None:
        await self._db.execute(
            update(User).where(User.id == user_id).values(password_hash=new_hash)
        )

    async def list_users(
        self, page: int, page_size: int, role: str | None = None, is_active: bool | None = None
    ) -> tuple[list[User], int]:
        from sqlalchemy import func

        q = select(User)
        if role:
            q = q.where(User.role == role)
        if is_active is not None:
            q = q.where(User.is_active == is_active)

        count_q = select(func.count()).select_from(q.subquery())
        count_result = await self._db.execute(count_q)
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        q = q.order_by(User.created_at.desc()).offset(offset).limit(page_size)
        result = await self._db.execute(q)
        return result.scalars().all(), total

    async def update(self, user: User, data: dict) -> User:
        for k, v in data.items():
            setattr(user, k, v)
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def soft_delete(self, user: User) -> None:
        user.is_active = False
        await self._db.flush()
