# app/core/config.py

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Campus Connect"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/campus_connect"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STRICT_MODE: bool = False

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    CORS_ORIGINS: str = "http://localhost:3000"

    # OTP
    OTP_EXPIRE_SECONDS: int = 300          # 5 minutes
    OTP_SIMULATE: bool = True              # True = skip real SMS in dev

    # SMS Provider (Twilio — fill in production)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
