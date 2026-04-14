"""Unit tests for security utilities."""

import pytest
from app.core.security import (
    hash_password,
    validate_password_complexity,
    verify_and_rehash_password,
    verify_password,
    create_access_token,
    decode_token,
)


class TestPasswordComplexity:
    def test_valid_password_passes(self):
        validate_password_complexity("Str0ng@Pass!")

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            validate_password_complexity("Short@1")

    def test_no_uppercase_raises(self):
        with pytest.raises(ValueError):
            validate_password_complexity("lowercase@1234!")

    def test_no_digit_raises(self):
        with pytest.raises(ValueError):
            validate_password_complexity("NoDigit@Pass!")

    def test_no_special_raises(self):
        with pytest.raises(ValueError):
            validate_password_complexity("NoSpecial1234a")

    def test_exactly_12_chars_passes(self):
        validate_password_complexity("Abc@1234abcd")


class TestPasswordHashing:
    def test_hash_verify_roundtrip(self):
        pw = "Secure@Password1"
        h = hash_password(pw)
        assert verify_password(pw, h)

    def test_wrong_password_fails(self):
        h = hash_password("Correct@Pass1")
        assert not verify_password("Wrong@Pass1", h)

    def test_new_hashes_use_argon2(self):
        """hash_password must produce Argon2 hashes, not bcrypt."""
        h = hash_password("Str0ng@Password!")
        assert h.startswith("$argon2"), f"Expected argon2 hash prefix, got: {h[:20]}"

    def test_legacy_bcrypt_hash_still_verifies(self):
        """Existing bcrypt hashes must remain verifiable after the algorithm migration."""
        from passlib.context import CryptContext
        bcrypt_ctx = CryptContext(schemes=["bcrypt"])
        pw = "Legacy@Pass1234"
        legacy_hash = bcrypt_ctx.hash(pw)
        # The main pwd_context (now argon2 + deprecated bcrypt) must verify it.
        assert verify_password(pw, legacy_hash)


class TestVerifyAndRehash:
    """verify_and_rehash_password upgrades bcrypt hashes transparently on login."""

    def _make_bcrypt_hash(self, pw: str) -> str:
        from passlib.context import CryptContext
        return CryptContext(schemes=["bcrypt"]).hash(pw)

    def test_correct_argon2_password_returns_valid_no_new_hash(self):
        """Fresh Argon2 hash: valid=True, new_hash=None (no upgrade needed)."""
        pw = "Correct@Pass1234"
        h = hash_password(pw)  # produces argon2
        is_valid, new_hash = verify_and_rehash_password(pw, h)
        assert is_valid is True
        assert new_hash is None  # already argon2; nothing to upgrade

    def test_wrong_password_returns_invalid_no_new_hash(self):
        """Wrong password: valid=False, new_hash=None regardless of scheme."""
        h = hash_password("Right@Pass1234")
        is_valid, new_hash = verify_and_rehash_password("Wrong@Pass1234", h)
        assert is_valid is False
        assert new_hash is None  # must never return a hash on failure

    def test_legacy_bcrypt_correct_password_returns_argon2_hash(self):
        """Correct password against bcrypt hash: valid=True, new_hash is an argon2 string."""
        pw = "Legacy@Pass1234"
        legacy_hash = self._make_bcrypt_hash(pw)
        is_valid, new_hash = verify_and_rehash_password(pw, legacy_hash)
        assert is_valid is True
        assert new_hash is not None
        assert new_hash.startswith("$argon2"), f"Expected argon2 upgrade hash, got: {new_hash[:20]}"

    def test_legacy_bcrypt_wrong_password_returns_no_hash(self):
        """Wrong password against bcrypt hash: valid=False, new_hash=None."""
        pw = "Correct@Pass1234"
        legacy_hash = self._make_bcrypt_hash(pw)
        is_valid, new_hash = verify_and_rehash_password("Wrong@Pass1234", legacy_hash)
        assert is_valid is False
        assert new_hash is None

    def test_upgraded_hash_verifies_with_plain_verify_password(self):
        """The returned new_hash can be verified normally, confirming roundtrip integrity."""
        pw = "Legacy@Pass1234"
        legacy_hash = self._make_bcrypt_hash(pw)
        _, new_hash = verify_and_rehash_password(pw, legacy_hash)
        assert new_hash is not None
        assert verify_password(pw, new_hash)


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token("user-123", "admin")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        from datetime import UTC, datetime, timedelta
        from jose import jwt
        from app.core.config import settings

        expired_payload = {
            "sub": "user-123",
            "role": "admin",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
            "type": "access",
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token(expired_token)
