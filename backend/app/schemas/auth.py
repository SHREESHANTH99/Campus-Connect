# app/schemas/auth.py

from pydantic import BaseModel, field_validator
import re


class RequestOTPSchema(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip spaces, dashes, parens
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        # Accept Indian numbers: +91XXXXXXXXXX or 10 digits
        if not re.match(r"^(\+91)?[6-9]\d{9}$", cleaned):
            raise ValueError("Enter a valid Indian mobile number.")
        # Normalize to +91XXXXXXXXXX
        if not cleaned.startswith("+91"):
            cleaned = "+91" + cleaned
        return cleaned


class VerifyOTPSchema(BaseModel):
    phone: str
    otp: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^(\+91)?[6-9]\d{9}$", cleaned):
            raise ValueError("Enter a valid Indian mobile number.")
        if not cleaned.startswith("+91"):
            cleaned = "+91" + cleaned
        return cleaned

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits.")
        return v


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    anonymous_username: str


class MeResponseSchema(BaseModel):
    id: str
    anonymous_username: str
    college_id: str | None
    karma: int
    status: str

    model_config = {"from_attributes": True}
