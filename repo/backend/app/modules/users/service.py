import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.encryption import decrypt_field, encrypt_field
from app.core.exceptions import ConflictError, NotFoundError
from app.core.masking import mask_email, mask_phone
from app.core.security import hash_password
from app.modules.instructors.models import Instructor
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserDetailResponse, UserResponse, UserUnmaskResponse, UserUpdate


def _build_response(user: User, admin: bool = False) -> UserResponse | UserDetailResponse:
    email_raw = decrypt_field(user.email_encrypted) if user.email_encrypted else None
    phone_raw = decrypt_field(user.phone_encrypted) if user.phone_encrypted else None

    data = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "email": mask_email(email_raw),
        "phone": mask_phone(phone_raw),
        "is_active": user.is_active,
        "last_login": user.last_login,
        "created_at": user.created_at,
    }
    if admin:
        return UserDetailResponse(**data)
    return UserResponse(**data)


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def create(self, payload: UserCreate, actor_id: str | None = None) -> UserResponse:
        existing = await self._repo.get_by_username(payload.username)
        if existing:
            raise ConflictError(f"Username '{payload.username}' already exists.")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
            email_encrypted=encrypt_field(payload.email) if payload.email else None,
            phone_encrypted=encrypt_field(payload.phone) if payload.phone else None,
        )
        user = await self._repo.create(user)

        if payload.role == UserRole.instructor:
            self._repo._db.add(Instructor(user_id=user.id))

        await log_audit(self._repo._db, actor_id or str(user.id), "user", str(user.id), "create")
        return _build_response(user, admin=True)

    async def get(self, user_id: str, admin: bool = False) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        return _build_response(user, admin=admin)

    async def list(self, page: int, page_size: int, role: str | None, is_active: bool | None):
        users, total = await self._repo.list_users(page, page_size, role, is_active)
        items = [_build_response(u, admin=True) for u in users]
        return items, total

    async def update(self, user_id: str, payload: UserUpdate, actor_id: str | None = None) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        data: dict = {}
        if payload.email is not None:
            data["email_encrypted"] = encrypt_field(payload.email)
        if payload.phone is not None:
            data["phone_encrypted"] = encrypt_field(payload.phone)
        if payload.is_active is not None:
            data["is_active"] = payload.is_active
        if payload.role is not None:
            data["role"] = payload.role

        user = await self._repo.update(user, data)

        if data.get("role") == UserRole.instructor:
            from sqlalchemy import select
            result = await self._repo._db.execute(
                select(Instructor).where(Instructor.user_id == user.id)
            )
            if not result.scalar_one_or_none():
                self._repo._db.add(Instructor(user_id=user.id))

        await log_audit(self._repo._db, actor_id or user_id, "user", user_id, "update",
                        new_value={k: str(v) for k, v in data.items() if k not in ("email_encrypted", "phone_encrypted")})
        return _build_response(user, admin=True)

    async def delete(self, user_id: str, actor_id: str | None = None) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        await self._repo.soft_delete(user)
        await log_audit(self._repo._db, actor_id or user_id, "user", user_id, "delete")

    async def unmask(self, user_id: str, actor_id: str, reason: str) -> UserUnmaskResponse:
        """Return unmasked PII for a user.  Requires an explicit reason and always
        writes an audit event — every call is recorded regardless of outcome,
        including attempts against non-existent user IDs."""
        user = await self._repo.get_by_id(user_id)

        if not user:
            # Audit the failed attempt before raising so that probing for valid
            # user IDs is always visible in the audit trail.
            await log_audit(
                self._repo._db,
                actor_id,
                "user",
                user_id,
                "unmask_pii_not_found",
                new_value={"reason": reason},
            )
            raise NotFoundError("User")

        email_raw = decrypt_field(user.email_encrypted) if user.email_encrypted else None
        phone_raw = decrypt_field(user.phone_encrypted) if user.phone_encrypted else None

        await log_audit(
            self._repo._db,
            actor_id,
            "user",
            user_id,
            "unmask_pii",
            new_value={"reason": reason, "fields": ["email", "phone"]},
        )
        return UserUnmaskResponse(
            id=user.id,
            username=user.username,
            email_unmasked=email_raw,
            phone_unmasked=phone_raw,
            reason=reason,
        )
