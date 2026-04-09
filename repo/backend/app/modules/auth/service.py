from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AccountLockedError, UnauthorizedError
from app.core.security import (
    blocklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_inactive,
    revoke_all_refresh_tokens,
    store_refresh_token,
    touch_last_seen,
    verify_and_consume_refresh_token,
    verify_password,
)
from app.modules.auth.schemas import TokenResponse
from app.modules.users.repository import UserRepository
from jose import JWTError


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)

    async def login(self, username: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_username(username)

        if not user:
            raise UnauthorizedError("Invalid credentials.")

        # Lockout check
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AccountLockedError(user.locked_until)

        if not verify_password(password, user.password_hash):
            attempts = user.failed_login_attempts + 1
            lock_until = None
            if attempts >= settings.LOGIN_MAX_ATTEMPTS:
                lock_until = datetime.now(UTC) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
                attempts = 0  # reset after locking
            await self._repo.update_login_failure(user.id, attempts, lock_until)
            raise UnauthorizedError("Invalid credentials.")

        if not user.is_active:
            raise UnauthorizedError("Account is inactive.")

        # Reset failure counter on success
        await self._repo.update_login_success(user.id)

        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))
        await store_refresh_token(str(user.id), refresh_token)
        await touch_last_seen(str(user.id))  # start inactivity clock

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid refresh token.")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type.")

        user_id: str = payload.get("sub")

        # Enforce inactivity before consuming the refresh token so the old token
        # is not burned on a rejected request.
        if await is_inactive(user_id):
            raise UnauthorizedError("Session expired due to inactivity.")

        valid = await verify_and_consume_refresh_token(user_id, refresh_token)
        if not valid:
            raise UnauthorizedError("Refresh token has been used or revoked.")

        user = await self._repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        new_access = create_access_token(str(user.id), user.role)
        new_refresh = create_refresh_token(str(user.id))
        await store_refresh_token(str(user.id), new_refresh)
        await touch_last_seen(str(user.id))  # slide the inactivity window on refresh

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    async def logout(self, access_token: str, user_id: str) -> None:
        await revoke_all_refresh_tokens(user_id)
        ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await blocklist_token(access_token, ttl)
        # Clear inactivity state so a re-login always gets a fresh window
        from app.core.security import get_redis
        await get_redis().delete(f"last_seen:{user_id}")

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedError()
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")
        new_hash = hash_password(new_password)
        await self._repo.update_password(user.id, new_hash)
        await revoke_all_refresh_tokens(user_id)
