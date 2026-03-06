# app/schemas/confession.py

from pydantic import BaseModel, field_validator
from datetime import datetime
from uuid import UUID
from app.models.confession import ConfessionCategory


class ConfessionCreateSchema(BaseModel):
    content: str
    category: ConfessionCategory = ConfessionCategory.general
    college_id: str | None = None  # if None → visible to all colleges

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Confession must be at least 10 characters.")
        if len(v) > 2000:
            raise ValueError("Confession cannot exceed 2000 characters.")
        return v


class ConfessionResponseSchema(BaseModel):
    id: UUID
    content: str
    category: ConfessionCategory
    college_id: str | None
    score: int
    upvotes: int
    downvotes: int
    created_at: datetime

    # We deliberately omit author_id from the response — full anonymity
    model_config = {"from_attributes": True}


class VoteSchema(BaseModel):
    vote_type: str   # "up" or "down"

    @field_validator("vote_type")
    @classmethod
    def validate_vote(cls, v: str) -> str:
        if v not in ("up", "down"):
            raise ValueError("vote_type must be 'up' or 'down'")
        return v
