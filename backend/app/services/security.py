"""Security utilities — encryption, hashing, JWT tokens."""

import hashlib
import hmac as hmac_mod
from datetime import datetime, timedelta, timezone
from functools import cache

import bcrypt
import jwt as pyjwt
from cryptography.fernet import Fernet

from app.config import settings


# --- Password hashing (bcrypt, direct — passlib is unmaintained) ---

def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT tokens (PyJWT) ---
JWT_ALGORITHM = "HS256"


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    to_encode.update({"exp": expire, "type": "access"})
    return pyjwt.encode(to_encode, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return pyjwt.encode(to_encode, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def create_guest_token(data: dict) -> str:
    """Create a guest JWT with 7-day TTL."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "guest"})
    return pyjwt.encode(to_encode, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = pyjwt.decode(
            token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM]
        )
        if payload.get("type") != expected_type:
            return None
        return payload
    except pyjwt.PyJWTError:
        return None


# --- Phone encryption (Fernet symmetric, cached instance) ---
@cache
def _get_fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt_phone(phone: str) -> str:
    """Encrypt a phone number for storage."""
    return _get_fernet().encrypt(phone.encode()).decode()


def decrypt_phone(encrypted: str) -> str:
    """Decrypt a stored phone number."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def hash_phone(phone: str) -> str:
    """Create an HMAC-SHA256 hash of a phone number for lookups.

    Uses jwt_secret_key as HMAC key, making rainbow-table precomputation
    infeasible without knowing the secret.
    """
    normalized = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )
    return hmac_mod.new(
        settings.jwt_secret_key.encode(),
        normalized.encode(),
        hashlib.sha256,
    ).hexdigest()


def mask_phone(phone: str) -> str:
    """Mask a phone number for display: ***4567"""
    if len(phone) < 4:
        return "***"
    return "***" + phone[-4:]
