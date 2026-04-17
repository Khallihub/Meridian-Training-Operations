"""Unit tests for auth service logic: token types, password rules."""

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.auth.schemas import LoginRequest, RefreshRequest, ChangePasswordRequest, TokenResponse


def test_access_token_has_correct_type():
    """Access token payload includes type='access'."""
    token = create_access_token("user-1", "admin")
    payload = decode_token(token)
    assert payload["type"] == "access"
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"


def test_refresh_token_has_correct_type():
    """Refresh token payload includes type='refresh'."""
    token = create_refresh_token("user-1")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-1"


def test_password_hash_and_verify_roundtrip():
    """Hashed password can be verified."""
    pw = "StrongPass@1234"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed)
    assert not verify_password("WrongPass@1234", hashed)


def test_login_request_schema():
    """LoginRequest accepts username and password."""
    req = LoginRequest(username="admin", password="pass")
    assert req.username == "admin"


def test_refresh_request_schema():
    """RefreshRequest accepts refresh_token."""
    req = RefreshRequest(refresh_token="some.jwt.token")
    assert req.refresh_token == "some.jwt.token"


def test_change_password_request_schema():
    """ChangePasswordRequest accepts current and new passwords."""
    req = ChangePasswordRequest(current_password="old", new_password="NewSecure@5678")
    assert req.current_password == "old"
    assert req.new_password == "NewSecure@5678"


def test_token_response_schema():
    """TokenResponse holds both tokens."""
    resp = TokenResponse(access_token="at", refresh_token="rt")
    assert resp.access_token == "at"
    assert resp.refresh_token == "rt"
