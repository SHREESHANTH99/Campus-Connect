# app/models/user.py

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
import enum


class UserStatus(str, enum.Enum):
    active = "active"
    banned = "banned"
    suspended = "suspended"


class User(Base):
    __tablename__ = "users"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identity (privacy-first) ─────────────────────────────────────────────
    # We store only a one-way hash of the phone number — never the raw number.
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # Anonymous username auto-generated (e.g. "Shadow_Panda_4721")
    anonymous_username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # ── College ──────────────────────────────────────────────────────────────
    # Verified via college email domain (future). Nullable until verified.
    college_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    college_email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Account health ───────────────────────────────────────────────────────
    karma: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        PgEnum(UserStatus, name="user_status"), default=UserStatus.active, nullable=False
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.anonymous_username}>"
