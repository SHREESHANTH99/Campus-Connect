# app/core/security.py

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from app.core.config import settings


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT token for an anonymous user."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.utcnow()}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Decode JWT and return the subject (user_id). Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ── Phone hashing (privacy-first) ────────────────────────────────────────────

def hash_phone(phone: str) -> str:
    """
    One-way hash of phone number — we never store raw phone numbers.
    Two users with same phone produce same hash for dedup, but hash
    cannot be reversed to recover the number.
    """
    return hashlib.sha256(phone.strip().encode()).hexdigest()
