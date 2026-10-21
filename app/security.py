"""Password hashing and credential helpers (Python standard library only).

PBKDF2-HMAC-SHA256 with a per-password random salt, stored as
``pbkdf2_sha256$<iterations>$<salt-hex>$<hash-hex>``. Verification uses a
constant-time comparison.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ITERATIONS = 260_000
ALGORITHM = "pbkdf2_sha256"
_MIN_PASSWORD_LENGTH = 8


class PasswordError(ValueError):
    """Raised when a password fails the workshop's own strength rules."""


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not password or not stored:
        return False
    try:
        algorithm, iterations_raw, salt, expected = stored.split("$", 3)
        iterations = int(iterations_raw)
    except (ValueError, AttributeError):
        return False
    if algorithm != ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(digest.hex(), expected)


def validate_password_strength(password: str) -> list[str]:
    if len(password) < _MIN_PASSWORD_LENGTH:
        return [f"Use at least {_MIN_PASSWORD_LENGTH} characters."]
    if password.strip() == "":
        return ["Enter a password."]
    return []
