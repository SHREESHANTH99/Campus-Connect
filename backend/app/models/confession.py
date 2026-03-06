# app/models/confession.py

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as PgEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class ConfessionCategory(str, enum.Enum):
    academics = "academics"
    love_crush = "love_crush"
    hostel_life = "hostel_life"
    professor_roast = "professor_roast"
    campus_secrets = "campus_secrets"
    career_anxiety = "career_anxiety"
    placement_tea = "placement_tea"
    general = "general"


class Confession(Base):
    __tablename__ = "confessions"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Content ──────────────────────────────────────────────────────────────
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ConfessionCategory] = mapped_column(
        PgEnum(ConfessionCategory, name="confession_category"),
        default=ConfessionCategory.general,
        nullable=False,
    )

    # ── Author (anonymous — FK to users) ─────────────────────────────────────
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author = relationship("User", backref="confessions")

    # ── College scoping ──────────────────────────────────────────────────────
    # NULL = visible to all colleges; set to restrict to one college feed
    college_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Engagement scores ────────────────────────────────────────────────────
    # Denormalized score for fast sorting (updated on every vote)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Moderation ───────────────────────────────────────────────────────────
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    is_removed: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Confession id={self.id} category={self.category}>"
