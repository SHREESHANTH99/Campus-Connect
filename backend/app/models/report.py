# app/models/report.py

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Enum as PgEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class ReportReason(str, enum.Enum):
    harassment = "harassment"
    explicit_content = "explicit_content"
    spam = "spam"
    hate_speech = "hate_speech"
    misinformation = "misinformation"
    other = "other"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(Base):
    __tablename__ = "reports"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Reporter ──────────────────────────────────────────────────────────────
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reporter = relationship("User", foreign_keys=[reporter_id])

    # ── What's being reported ─────────────────────────────────────────────────
    # target_type: "confession" | "chat_message" | "user"
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # ── Report details ────────────────────────────────────────────────────────
    reason: Mapped[ReportReason] = mapped_column(
        PgEnum(ReportReason, name="report_reason"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Moderation status ─────────────────────────────────────────────────────
    status: Mapped[ReportStatus] = mapped_column(
        PgEnum(ReportStatus, name="report_status"),
        default=ReportStatus.pending,
        nullable=False,
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mod_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Report id={self.id} target={self.target_type}/{self.target_id} status={self.status}>"
