"""Unit tests for security utilities."""

import pytest
from app.core.security import (
    hash_password,
    validate_password_complexity,
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
