# app/models/chat_session.py

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Enum as PgEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class ChatMode(str, enum.Enum):
    study = "study"
    vent = "vent"
    fun = "fun"


class ChatSessionStatus(str, enum.Enum):
    waiting = "waiting"      # one user waiting for a match
    active = "active"        # both users connected
    ended = "ended"          # session closed


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Participants ──────────────────────────────────────────────────────────
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_b_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user_a = relationship("User", foreign_keys=[user_a_id])
    user_b = relationship("User", foreign_keys=[user_b_id])

    # ── Chat configuration ────────────────────────────────────────────────────
    mode: Mapped[ChatMode] = mapped_column(
        PgEnum(ChatMode, name="chat_mode"), default=ChatMode.fun, nullable=False
    )
    status: Mapped[ChatSessionStatus] = mapped_column(
        PgEnum(ChatSessionStatus, name="chat_session_status"),
        default=ChatSessionStatus.waiting,
        nullable=False,
    )

    # College-scoped matching (NULL = pan-India matching)
    college_id: Mapped[str | None] = mapped_column(nullable=True)

    # ── Privacy ───────────────────────────────────────────────────────────────
    # Messages are NOT stored in DB — they live in Redis/WebSocket only.
    # This table tracks session metadata only.
    messages_wiped: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} mode={self.mode} status={self.status}>"
