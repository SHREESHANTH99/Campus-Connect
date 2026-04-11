# app/api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_phone, create_access_token
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.middleware.rate_limit import limiter
from app.schemas.auth import RequestOTPSchema, VerifyOTPSchema, TokenResponseSchema, MeResponseSchema
from app.services import otp_service, auth_service, cache_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/request-otp", summary="Send OTP to phone number")
def request_otp(
    payload: RequestOTPSchema,
    db: Session = Depends(get_db),
    _: None = Depends(limiter("otp_request", limit=3, window_seconds=600)),
):
    """
    Step 1 of login flow.
    - Accepts phone number
    - Generates 6-digit OTP, stores in Redis (5 min TTL)
    - In dev mode: OTP is printed to server logs (OTP_SIMULATE=True)
    - In prod: OTP is sent via Twilio SMS
    """
    phone_hash = hash_phone(payload.phone)
    otp = otp_service.generate_and_store_otp(phone_hash)
    otp_service.send_otp_sms(payload.phone, otp)

    return {"message": "OTP sent successfully.", "expires_in_seconds": 300}


@router.post("/verify-otp", response_model=TokenResponseSchema, summary="Verify OTP and get JWT")
def verify_otp(payload: VerifyOTPSchema, db: Session = Depends(get_db)):
    """
    Step 2 of login flow.
    - Verifies OTP against Redis
    - Creates user if first time (anonymous, no real name stored)
    - Returns JWT access token
    """
    phone_hash = hash_phone(payload.phone)

    is_valid = otp_service.verify_otp(phone_hash, payload.otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please try again.",
        )

    user, is_new = auth_service.get_or_create_user(db, payload.phone)
    token = create_access_token(subject=str(user.id))

    return TokenResponseSchema(
        access_token=token,
        is_new_user=is_new,
        anonymous_username=user.anonymous_username,
    )


@router.get("/me", response_model=MeResponseSchema, summary="Get current user profile")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's anonymous profile.
    No real-world identity is ever included in this response.
    """
    cached = cache_service.get_user_karma(str(current_user.id))
    karma = cached.get("karma") if cached else current_user.karma
    cache_service.set_user_karma(str(current_user.id), int(karma))

    return MeResponseSchema(
        id=str(current_user.id),
        anonymous_username=current_user.anonymous_username,
        college_id=current_user.college_id,
        karma=int(karma),
        status=current_user.status.value,
    )
