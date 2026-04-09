"""Fernet symmetric encryption for sensitive fields stored in the database."""

import base64
import os

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        # Fallback: deterministic key derived from SECRET_KEY (dev only, not for prod)
        import hashlib
        raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_field(value: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    if not value:
        return value
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Returns plaintext."""
    if not ciphertext:
        return ciphertext
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def generate_fernet_key() -> str:
    """Generate a new Fernet key (call during initial setup)."""
    return Fernet.generate_key().decode()
