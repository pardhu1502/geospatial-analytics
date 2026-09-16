"""
Unit tests for app/core/security.py: password hashing and JWT
create/decode. No database or network needed.
"""

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext_and_verifies():
    hashed = hash_password("CorrectHorseBatteryStaple")
    assert hashed != "CorrectHorseBatteryStaple"
    assert verify_password("CorrectHorseBatteryStaple", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_same_password_hashes_differently_each_time():
    # bcrypt salts each hash, so two hashes of the same password must differ.
    assert hash_password("same-password") != hash_password("same-password")


def test_create_and_decode_access_token_round_trips_subject():
    token = create_access_token(subject=42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_decode_access_token_rejects_bad_signature():
    token = create_access_token(subject=1)
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(Exception):
        decode_access_token(tampered)


def test_token_is_signed_with_configured_algorithm_and_secret():
    token = create_access_token(subject=7)
    # Decoding manually with the same secret/algorithm should work...
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == "7"
    # ...but decoding with the wrong secret should fail.
    with pytest.raises(Exception):
        jwt.decode(token, "wrong-secret", algorithms=[settings.JWT_ALGORITHM])
