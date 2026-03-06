# app/services/otp_service.py

import random
import redis
from app.core.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)


def _otp_key(phone_hash: str) -> str:
    return f"otp:{phone_hash}"


def generate_and_store_otp(phone_hash: str) -> str:
    """
    Generate a 6-digit OTP, store it in Redis with TTL, and return it.
    In production: send via Twilio instead of returning it.
    """
    otp = str(random.randint(100000, 999999))
    _redis.setex(_otp_key(phone_hash), settings.OTP_EXPIRE_SECONDS, otp)
    return otp


def verify_otp(phone_hash: str, otp: str) -> bool:
    """
    Verify that the given OTP matches what's stored in Redis.
    Deletes the OTP after a successful match (one-time use).
    """
    stored = _redis.get(_otp_key(phone_hash))
    if stored and stored == otp:
        _redis.delete(_otp_key(phone_hash))
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
