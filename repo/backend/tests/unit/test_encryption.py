"""Unit tests for field encryption."""

import os
import pytest


def test_encrypt_decrypt_roundtrip():
    os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-here!!"
    from app.core.encryption import encrypt_field, decrypt_field
    plain = "test@example.com"
    encrypted = encrypt_field(plain)
    assert encrypted != plain
    assert decrypt_field(encrypted) == plain


def test_empty_string_passthrough():
    from app.core.encryption import encrypt_field, decrypt_field
    assert encrypt_field("") == ""
    assert decrypt_field("") == ""


def test_different_values_produce_different_ciphertext():
    from app.core.encryption import encrypt_field
    assert encrypt_field("valueA") != encrypt_field("valueB")
