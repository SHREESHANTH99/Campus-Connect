# app/services/otp_service.py

import random
import redis
from datetime import datetime, timedelta
from app.core.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
_memory_otp_store: dict[str, tuple[str, datetime]] = {}


def _otp_key(phone_hash: str) -> str:
    return f"otp:{phone_hash}"


def generate_and_store_otp(phone_hash: str) -> str:
    """
    Generate a 6-digit OTP, store it in Redis with TTL, and return it.
    In production: send via Twilio instead of returning it.
    """
    otp = str(random.randint(100000, 999999))
    try:
        _redis.setex(_otp_key(phone_hash), settings.OTP_EXPIRE_SECONDS, otp)
    except Exception:
        if settings.REDIS_STRICT_MODE:
            raise RuntimeError("Redis unavailable and strict mode is enabled for OTP storage")
        _memory_otp_store[_otp_key(phone_hash)] = (
            otp,
            datetime.utcnow() + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
        )
    return otp


def verify_otp(phone_hash: str, otp: str) -> bool:
    """
    Verify that the given OTP matches what's stored in Redis.
    Deletes the OTP after a successful match (one-time use).
    """
    key = _otp_key(phone_hash)
    try:
        stored = _redis.get(key)
        if stored and stored == otp:
            _redis.delete(key)
            return True
    except Exception:
        if settings.REDIS_STRICT_MODE:
            raise RuntimeError("Redis unavailable and strict mode is enabled for OTP verification")
        entry = _memory_otp_store.get(key)
        if not entry:
            return False
        stored_otp, expires_at = entry
        if datetime.utcnow() > expires_at:
            _memory_otp_store.pop(key, None)
            return False
        if stored_otp == otp:
            _memory_otp_store.pop(key, None)
            return True
    return False


def send_otp_sms(phone: str, otp: str) -> None:
    """
    Send OTP via Twilio in production.
    Skipped entirely when OTP_SIMULATE=True (dev mode).
    """
    if settings.OTP_SIMULATE:
        print(f"[DEV] OTP for {phone}: {otp}")   # visible in server logs
        return

    from twilio.rest import Client
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        body=f"Your Campus Connect OTP is: {otp}. Valid for 5 minutes.",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone,
    )
