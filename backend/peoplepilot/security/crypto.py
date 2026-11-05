"""Encryption at rest, lookup hashing, and password hashing."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings

_ph = PasswordHasher()
# Used so that login with an unknown email costs the same time as a wrong password.
_DUMMY_HASH = _ph.hash("not-a-real-password-" + secrets.token_hex(8))


def _fernet() -> Fernet:
    return Fernet(get_settings().data_key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # wrong key or tampered ciphertext
        raise ValueError("cannot decrypt value") from exc


def encrypt_json(data: dict) -> str:
    return encrypt(json.dumps(data, separators=(",", ":")))


def decrypt_json(token: str) -> dict:
    return json.loads(decrypt(token))


def lookup_hash(value: str) -> str:
    """Keyed hash so identifiers can be looked up without storing them in clear text."""
    return hmac.new(get_settings().hmac_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _ph.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
