# app/api/confessions.py  — Phase 2 complete rewrite

from uuid import UUID
from fastapi import APIRouter, Depends, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.confession import ConfessionCategory
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.confession import (
    ConfessionCreateSchema,
    ConfessionResponseSchema,
    ConfessionDetailSchema,
    FeedResponseSchema,
    VoteResponseSchema,
    VoteSchema,
    ReactionSchema,
    CommentCreateSchema,
    CommentResponseSchema,
    ReportSchema,
)
from app.services import confession_service

router = APIRouter(prefix="/confessions", tags=["Confessions"])


# ── POST /confessions ─────────────────────────────────────────────────────────

@router.post("/", response_model=ConfessionResponseSchema, status_code=status.HTTP_201_CREATED,
             summary="Post an anonymous confession")
def create_confession(payload: ConfessionCreateSchema, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user),
                      _: None = Depends(limiter("confession_create", limit=1, window_seconds=120))):
    """
    Posts a new anonymous confession.
    - Runs multi-layer moderation before storing
    - Author identity is NEVER exposed in responses
    - Rejected confessions return HTTP 400 with a reason
    """
    return confession_service.create_confession(db=db, author=user, content=payload.content,
                                                category=payload.category, college_id=payload.college_id)


# ── GET /confessions ──────────────────────────────────────────────────────────

@router.get("/", response_model=FeedResponseSchema, summary="Get confession feed")
def get_feed(
    sort: str = Query("hot", enum=["hot", "new", "top", "trending"],
                      description="hot | new | top | trending"),
    category:   Optional[ConfessionCategory] = Query(None),
    college_id: Optional[str]               = Query(None),
    cursor:     Optional[str]               = Query(None),
    limit:      int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Paginated feed with 4 sort modes.
    Use next_cursor from response as ?cursor= for the next page.
    trending is Redis-cached (refreshed every 5 min) and has no cursor.
    """
    items, next_cursor = confession_service.get_feed(db=db, sort=sort, category=category,
                                                     college_id=college_id, cursor=cursor, limit=limit)
    return FeedResponseSchema(items=items, next_cursor=next_cursor, total_hint=None)


# ── GET /confessions/trending/weekly ─────────────────────────────────────────

@router.get("/trending/weekly", response_model=list[ConfessionResponseSchema],
            summary="Top confessions of the past 7 days")
def weekly_trending(college_id: Optional[str] = Query(None), limit: int = Query(10, ge=1, le=30),
                    db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from app.models.confession import Confession, ModerationStatus
    week_ago = datetime.utcnow() - timedelta(days=7)
    q = db.query(Confession).filter(Confession.is_removed == False,
                                    Confession.moderation_status != ModerationStatus.rejected,
                                    Confession.created_at >= week_ago)
    if college_id:
        q = q.filter(Confession.college_id == college_id)
    return q.order_by(Confession.score.desc()).limit(limit).all()


# ── GET /confessions/{id} ─────────────────────────────────────────────────────

@router.get("/{confession_id}", response_model=ConfessionDetailSchema,
            summary="Get a single confession with comments")
def get_confession(confession_id: UUID, background_tasks: BackgroundTasks,
                   db: Session = Depends(get_db)):
    """Returns confession + comments. View count is incremented in background."""
    confession = confession_service.get_confession(db, confession_id)
    background_tasks.add_task(confession_service.record_view, db, confession_id)
    comments = confession_service.get_comments(db, confession_id)
    resp = ConfessionDetailSchema.model_validate(confession)
    resp.comments = [CommentResponseSchema.model_validate(c) for c in comments]
    return resp


# ── POST /confessions/{id}/vote ───────────────────────────────────────────────

@router.post("/{confession_id}/vote", response_model=VoteResponseSchema,
             summary="Upvote or downvote (toggle-aware)")
def vote(confession_id: UUID, payload: VoteSchema, db: Session = Depends(get_db),
         user: User = Depends(get_current_user),
         _: None = Depends(limiter("confession_vote", limit=30, window_seconds=60))):
    """Same vote twice = untoggle. Opposite vote = flip. Trending score updates instantly."""
    result = confession_service.vote(db, confession_id, user, payload.vote_type)
    return VoteResponseSchema(**result)


# ── POST /confessions/{id}/react ─────────────────────────────────────────────

@router.post("/{confession_id}/react", summary="Add emoji reaction (no auth needed)")
def react(
    confession_id: UUID,
    payload: ReactionSchema,
    db: Session = Depends(get_db),
    _: None = Depends(limiter("confession_react", limit=10, window_seconds=60)),
):
    """Valid reactions: relatable | shocking | supportive | spicy"""
    reactions = confession_service.add_reaction(db, confession_id, payload.reaction)
    return {"reactions": reactions}


# ── POST /confessions/{id}/comments ──────────────────────────────────────────

@router.post("/{confession_id}/comments", response_model=CommentResponseSchema,
             status_code=status.HTTP_201_CREATED, summary="Post anonymous comment")
def create_comment(confession_id: UUID, payload: CommentCreateSchema,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user),
                   _: None = Depends(limiter("confession_comment", limit=15, window_seconds=300))):
    """Set parent_id for replies. Max 1 level of threading."""
    comment = confession_service.create_comment(db=db, confession_id=confession_id, author=user,
                                                content=payload.content, parent_id=payload.parent_id)
    return CommentResponseSchema.model_validate(comment)


# ── GET /confessions/{id}/comments ───────────────────────────────────────────

@router.get("/{confession_id}/comments", response_model=list[CommentResponseSchema],
            summary="Get comments for a confession")
def get_comments(confession_id: UUID, limit: int = Query(30, ge=1, le=100),
                 db: Session = Depends(get_db)):
    comments = confession_service.get_comments(db, confession_id, limit=limit)
    return [CommentResponseSchema.model_validate(c) for c in comments]


# ── POST /confessions/{id}/report ────────────────────────────────────────────

@router.post("/{confession_id}/report", status_code=status.HTTP_201_CREATED,
             summary="Report a confession")
def report(confession_id: UUID, payload: ReportSchema, db: Session = Depends(get_db),
           user: User = Depends(get_current_user),
           _: None = Depends(limiter("confession_report", limit=5, window_seconds=3600))):
    """5 reports = auto-flagged. 10 reports = auto-removed. One report per user."""
    confession_service.report_confession(db=db, confession_id=confession_id, reporter=user,
                                         reason=payload.reason, description=payload.description)
    return {"message": "Reported. Our moderation team will review this shortly."}
