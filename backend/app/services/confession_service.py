# app/services/confession_service.py
# Phase 2 — Complete confession business logic

import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.confession import Confession, ConfessionCategory, ModerationStatus
from app.models.comment import Comment
from app.models.vote import Vote, VoteType
from app.models.report import Report, ReportReason
from app.models.user import User
from app.services import moderation_service, trending_service
from app.services import cache_service


def _serialize_confession(c: Confession) -> dict:
    return {
        "id": str(c.id),
        "content": c.content,
        "category": c.category.value,
        "college_id": c.college_id,
        "score": c.score,
        "upvotes": c.upvotes,
        "downvotes": c.downvotes,
        "view_count": c.view_count,
        "comment_count": c.comment_count,
        "reactions": c.reactions,
        "trending_score": c.trending_score,
        "created_at": c.created_at.isoformat(),
    }


# ── CREATE ────────────────────────────────────────────────────────────────────

def create_confession(
    db: Session,
    author: User,
    content: str,
    category: ConfessionCategory,
    college_id: str | None = None,
) -> Confession:
    """
    Run moderation check, then persist the confession.
    Raises 400 if content is rejected.
    """
    # 1. Moderation
    mod = moderation_service.moderate(content)

    if mod.should_reject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Your confession was rejected by our content filter. Reason: {mod.reasons[0] if mod.reasons else 'Policy violation.'}",
        )

    # 2. Persist
    confession = Confession(
        content=content,
        category=category,
        college_id=college_id or author.college_id,
        author_id=author.id,
        moderation_status=(
            ModerationStatus.flagged if mod.should_flag else ModerationStatus.approved
        ),
        moderation_score=mod.score,
    )
    db.add(confession)
    db.commit()
    db.refresh(confession)

    # 3. Invalidate trending cache since a new post appeared
    trending_service.invalidate_trending_cache()
    cache_service.invalidate_hot_feed()

    return confession


# ── READ: paginated feed ──────────────────────────────────────────────────────

def get_feed(
    db: Session,
    sort:       str             = "hot",
    category:   ConfessionCategory | None = None,
    college_id: str | None      = None,
    cursor:     str | None      = None,   # ISO timestamp for cursor pagination
    limit:      int             = 20,
) -> tuple[list[Confession], str | None]:
    """
    Returns (confessions, next_cursor).
    next_cursor is None when there are no more results.

    sort options:
      hot      — score DESC + age tiebreak
      new      — created_at DESC
      top      — upvotes DESC (all-time)
      trending — pre-computed trending_score DESC (served from Redis cache)
    """
    if sort == "trending":
        # Fast path — Redis cache
        cached = trending_service.get_trending_feed_cached(db, limit=limit)
        # Apply filters on cached data if needed
        if category:
            cached = [c for c in cached if c["category"] == category.value]
        if college_id:
            cached = [c for c in cached if c.get("college_id") == college_id]
        return cached, None  # no cursor for trending (pre-computed list)

    # DB query path
    if sort == "hot":
        hot_cached = cache_service.get_hot_feed(
            cursor=cursor,
            category=category.value if category else None,
            college_id=college_id,
            limit=limit,
        )
        if hot_cached:
            return hot_cached["items"], hot_cached.get("next_cursor")

    q = (
        db.query(Confession)
        .filter(
            Confession.is_removed == False,
            Confession.moderation_status != ModerationStatus.rejected,
        )
    )

    if category:
        q = q.filter(Confession.category == category)
    if college_id:
        q = q.filter(Confession.college_id == college_id)

    # Cursor-based pagination (more stable than offset under active writes)
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format.")

        if sort in ("hot", "new"):
            q = q.filter(Confession.created_at < cursor_dt)
        elif sort == "top":
            # For "top" we use upvotes cursor not time — keep it simple with offset fallback
            pass

    # Sorting
    if sort == "hot":
        q = q.order_by(Confession.score.desc(), Confession.created_at.desc())
    elif sort == "new":
        q = q.order_by(Confession.created_at.desc())
    elif sort == "top":
        q = q.order_by(Confession.upvotes.desc(), Confession.created_at.desc())

    results = q.limit(limit + 1).all()   # fetch one extra to detect next page

    has_more = len(results) > limit
    items = results[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = last.created_at.isoformat()

    if sort == "hot":
        cache_service.set_hot_feed(
            cursor=cursor,
            category=category.value if category else None,
            college_id=college_id,
            limit=limit,
            payload={
                "items": [_serialize_confession(i) for i in items],
                "next_cursor": next_cursor,
            },
        )

    return items, next_cursor


# ── READ: single confession ───────────────────────────────────────────────────

def get_confession(db: Session, confession_id: uuid.UUID) -> Confession:
    c = db.query(Confession).filter(
        Confession.id == confession_id,
        Confession.is_removed == False,
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Confession not found.")
    return c


def record_view(db: Session, confession_id: uuid.UUID) -> None:
    """Increment view_count. Fire-and-forget — called in background."""
    db.query(Confession).filter(Confession.id == confession_id).update(
        {Confession.view_count: Confession.view_count + 1}
    )
    db.commit()


# ── VOTE ──────────────────────────────────────────────────────────────────────

def vote(
    db: Session,
    confession_id: uuid.UUID,
    user: User,
    vote_type: str,   # "up" | "down"
) -> dict:
    """
    Toggle-aware voting:
      - No prior vote → create vote
      - Same vote again → remove vote (untoggle)
      - Different vote → flip vote
    Returns updated counts.
    """
    confession = get_confession(db, confession_id)
    vt = VoteType(vote_type)

    existing = db.query(Vote).filter(
        Vote.user_id       == user.id,
        Vote.confession_id == confession_id,
    ).first()

    if existing:
        if existing.vote_type == vt:
            # Untoggle
            db.delete(existing)
            if vt == VoteType.up:
                confession.upvotes   = max(0, confession.upvotes - 1)
            else:
                confession.downvotes = max(0, confession.downvotes - 1)
        else:
            # Flip
            existing.vote_type = vt
            if vt == VoteType.up:
                confession.upvotes   += 1
                confession.downvotes  = max(0, confession.downvotes - 1)
            else:
                confession.downvotes += 1
                confession.upvotes   = max(0, confession.upvotes - 1)
    else:
        db.add(Vote(user_id=user.id, confession_id=confession_id, vote_type=vt))
        if vt == VoteType.up:
            confession.upvotes   += 1
        else:
            confession.downvotes += 1

    confession.score         = confession.upvotes - confession.downvotes
    confession.trending_score = trending_service.compute_trending_score(
        score=confession.score,
        comment_count=confession.comment_count,
        view_count=confession.view_count,
        reactions=confession.reactions or {},
        created_at=confession.created_at,
    )
    db.commit()
    cache_service.invalidate_hot_feed()
    trending_service.invalidate_trending_cache()

    return {
        "score":     confession.score,
        "upvotes":   confession.upvotes,
        "downvotes": confession.downvotes,
    }


# ── REACT ─────────────────────────────────────────────────────────────────────

VALID_REACTIONS = {"relatable", "shocking", "supportive", "spicy"}


def add_reaction(
    db: Session,
    confession_id: uuid.UUID,
    reaction: str,
) -> dict:
    """Increment an emoji reaction counter. No auth required — casual engagement."""
    if reaction not in VALID_REACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reaction. Choose from: {', '.join(VALID_REACTIONS)}",
        )
    confession = get_confession(db, confession_id)
    reactions  = dict(confession.reactions or {})
    reactions[reaction] = reactions.get(reaction, 0) + 1
    confession.reactions = reactions
    db.commit()
    cache_service.invalidate_hot_feed()
    trending_service.invalidate_trending_cache()
    return reactions


# ── COMMENT ───────────────────────────────────────────────────────────────────

def create_comment(
    db: Session,
    confession_id: uuid.UUID,
    author: User,
    content: str,
    parent_id: uuid.UUID | None = None,
) -> Comment:
    confession = get_confession(db, confession_id)

    # Moderation
    mod = moderation_service.moderate_comment(content)
    if mod.should_reject:
        raise HTTPException(
            status_code=400,
            detail=f"Comment rejected: {mod.reasons[0] if mod.reasons else 'Policy violation.'}",
        )

    # Validate parent exists if threading
    if parent_id:
        parent = db.query(Comment).filter(
            Comment.id == parent_id,
            Comment.confession_id == confession_id,
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found.")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="Replies cannot be nested more than 1 level.")

    comment = Comment(
        confession_id=confession_id,
        author_id=author.id,
        content=content,
        parent_id=parent_id,
        moderation_score=mod.score,
    )
    db.add(comment)

    # Update denormalised comment count
    confession.comment_count += 1
    db.commit()
    db.refresh(comment)
    cache_service.invalidate_hot_feed()
    trending_service.invalidate_trending_cache()
    return comment


def get_comments(
    db: Session,
    confession_id: uuid.UUID,
    limit: int = 30,
) -> list[Comment]:
    """Returns top-level comments with their replies pre-loaded."""
    return (
        db.query(Comment)
        .filter(
            Comment.confession_id == confession_id,
            Comment.parent_id     == None,
            Comment.is_removed    == False,
        )
        .order_by(Comment.upvotes.desc(), Comment.created_at.asc())
        .limit(limit)
        .all()
    )


# ── REPORT ───────────────────────────────────────────────────────────────────

def report_confession(
    db: Session,
    confession_id: uuid.UUID,
    reporter: User,
    reason: ReportReason,
    description: str | None = None,
) -> None:
    confession = get_confession(db, confession_id)

    # Prevent duplicate reports from same user
    existing_report = db.query(Report).filter(
        Report.reporter_id == reporter.id,
        Report.target_id   == confession_id,
        Report.target_type == "confession",
    ).first()
    if existing_report:
        raise HTTPException(status_code=400, detail="You already reported this confession.")

    db.add(Report(
        reporter_id=reporter.id,
        target_type="confession",
        target_id=confession_id,
        reason=reason,
        description=description,
    ))

    # Increment report counter and auto-flag at threshold
    confession.report_count += 1
    if confession.report_count >= 5:
        confession.is_flagged = True
    if confession.report_count >= 10:
        # Auto-remove at high report volume — human review still required
        confession.is_removed = True

    db.commit()
    cache_service.invalidate_hot_feed()
    trending_service.invalidate_trending_cache()
