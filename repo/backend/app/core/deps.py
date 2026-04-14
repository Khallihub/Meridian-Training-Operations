"""FastAPI dependency injection: current user, role guards."""

from __future__ import annotations

from fastapi import Depends, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token, is_inactive, is_token_blocklisted, touch_last_seen

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.users.repository import UserRepository

    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.")

    if await is_token_blocklisted(token):
        raise UnauthorizedError("Token has been revoked.")

    user_id: str = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()

    if await is_inactive(user_id):
        raise UnauthorizedError("Session expired due to inactivity.")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    await touch_last_seen(user_id)
    return user


def require_roles(*roles: str):
    """Returns a dependency that enforces role membership."""

    async def _check(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise ForbiddenError()
        return current_user

    return _check


async def get_ws_user(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """Authenticate WebSocket connections via ?token= query param.

    Inactivity is NOT checked here — the JWT expiry is the correct security
    gate for long-lived WebSocket connections.  The Redis-based is_inactive
    check is only meaningful for REST endpoints and fails spuriously after a
    Redis restart (all keys gone even though sessions are still valid).
    """
    from app.modules.users.repository import UserRepository

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        raise UnauthorizedError("Missing token.")

    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=4001)
        raise UnauthorizedError("Invalid token.")

    if payload.get("type") != "access":
        await websocket.close(code=4001)
        raise UnauthorizedError()

    if await is_token_blocklisted(token):
        await websocket.close(code=4001)
        raise UnauthorizedError("Token has been revoked.")

    user_id: str = payload.get("sub")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        await websocket.close(code=4001)
        raise UnauthorizedError()

    # Refresh the activity window now that we have a live connection
    await touch_last_seen(user_id)
    return user
