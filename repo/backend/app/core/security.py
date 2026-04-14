import re
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Argon2id is the PRD-required algorithm.  bcrypt is listed as deprecated so
# existing bcrypt hashes can still be verified and are transparently upgraded
# to argon2 on the next successful login (passlib re-hashes on verify when the
# stored scheme is deprecated).
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated=["bcrypt"])

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

_PASSWORD_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]).{12,}$"
)


def validate_password_complexity(password: str) -> None:
    """Raise ValueError if password does not meet complexity rules."""
    if not _PASSWORD_RE.match(password):
        raise ValueError(
            "Password must be at least 12 characters and contain uppercase, "
            "lowercase, digit, and special character."
        )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_and_rehash_password(plain: str, hashed: str) -> tuple[bool, str | None]:
    """Verify a password and transparently upgrade deprecated hashes.

    Returns ``(is_valid, new_hash)``.

    - ``is_valid`` is True when the plain password matches ``hashed``.
    - ``new_hash`` is non-None **only** when the stored hash used a deprecated
      scheme (bcrypt) and the plain password was correct.  The caller must
      persist ``new_hash`` to the database so the next login uses Argon2id.
    - ``new_hash`` is always None on a failed verification so callers cannot
      accidentally write a hash for the wrong password.

    Example (auth service login)::

        is_valid, new_hash = verify_and_rehash_password(password, user.password_hash)
        if not is_valid:
            ...  # handle failure
        if new_hash:
            await repo.update_password(user.id, new_hash)  # silent upgrade
    """
    is_valid, new_hash = pwd_context.verify_and_update(plain, hashed)
    # Guard: only return a new hash on success
    return is_valid, (new_hash if is_valid and new_hash else None)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


async def blocklist_token(token: str, ttl_seconds: int) -> None:
    r = get_redis()
    await r.setex(f"blocklist:{token}", ttl_seconds, "1")


async def is_token_blocklisted(token: str) -> bool:
    r = get_redis()
    return await r.exists(f"blocklist:{token}") == 1


# ---------------------------------------------------------------------------
# Refresh token store (hashed in Redis)
# ---------------------------------------------------------------------------

import hashlib


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def store_refresh_token(user_id: str, token: str) -> None:
    r = get_redis()
    hashed = _hash_token(token)
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await r.setex(f"refresh:{user_id}:{hashed}", ttl, "1")


async def verify_and_consume_refresh_token(user_id: str, token: str) -> bool:
    r = get_redis()
    hashed = _hash_token(token)
    key = f"refresh:{user_id}:{hashed}"
    if await r.exists(key):
        await r.delete(key)
        return True
    return False


async def revoke_all_refresh_tokens(user_id: str) -> None:
    r = get_redis()
    async for key in r.scan_iter(f"refresh:{user_id}:*"):
        await r.delete(key)


# ---------------------------------------------------------------------------
# Inactivity tracking (sliding 30-minute window)
# ---------------------------------------------------------------------------

async def touch_last_seen(user_id: str) -> None:
    """Record current timestamp as last activity for the user."""
    r = get_redis()
    ttl = settings.INACTIVITY_TIMEOUT_MINUTES * 60 + 60  # a little over the window
    await r.setex(f"last_seen:{user_id}", ttl, datetime.now(UTC).isoformat())


async def is_inactive(user_id: str) -> bool:
    """Return True if the user has exceeded the inactivity timeout.

    A missing key means the window has already expired (Redis TTL elapsed) or the
    user logged out — both cases must be treated as inactive, not as a fresh login.
    Fresh logins are protected because login() always calls touch_last_seen() before
    returning tokens, so a legitimate first request will always find the key present.
    """
    r = get_redis()
    raw = await r.get(f"last_seen:{user_id}")
    if raw is None:
        return True  # key expired → idle window exceeded; force re-login
    last_seen = datetime.fromisoformat(raw)
    elapsed = (datetime.now(UTC) - last_seen).total_seconds() / 60
    return elapsed > settings.INACTIVITY_TIMEOUT_MINUTES
