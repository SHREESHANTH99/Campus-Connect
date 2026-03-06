# app/models/vote.py

import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class VoteType(str, enum.Enum):
    up = "up"
    down = "down"


class Vote(Base):
    __tablename__ = "votes"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    confession_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("confessions.id", ondelete="CASCADE"), nullable=False
    )

    vote_type: Mapped[VoteType] = mapped_column(
        PgEnum(VoteType, name="vote_type"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ORM helpers
    user = relationship("User", backref="votes")
    confession = relationship("Confession", backref="votes")

    # ── Constraints ──────────────────────────────────────────────────────────
    # One vote per user per confession — enforced at DB level
    __table_args__ = (
        UniqueConstraint("user_id", "confession_id", name="uq_vote_user_confession"),
    )

    def __repr__(self) -> str:
        return f"<Vote {self.vote_type} user={self.user_id} confession={self.confession_id}>"
