# app/api/confessions.py

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.confession import Confession, ConfessionCategory
from app.models.vote import Vote, VoteType
from app.models.report import Report, ReportReason
from app.models.user import User
from app.schemas.confession import ConfessionCreateSchema, ConfessionResponseSchema, VoteSchema

router = APIRouter(prefix="/confessions", tags=["Confessions"])


# ── POST /confessions — Create a new confession ───────────────────────────────

@router.post("/", response_model=ConfessionResponseSchema, status_code=status.HTTP_201_CREATED)
def create_confession(
    payload: ConfessionCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post an anonymous confession. Author identity is stored internally only."""
    confession = Confession(
        content=payload.content,
        category=payload.category,
        college_id=payload.college_id or current_user.college_id,
        author_id=current_user.id,
    )
    db.add(confession)
    db.commit()
    db.refresh(confession)
    return confession


# ── GET /confessions — List confessions (feed) ────────────────────────────────

@router.get("/", response_model=list[ConfessionResponseSchema])
def list_confessions(
    category: ConfessionCategory | None = Query(None),
    college_id: str | None = Query(None),
    sort: str = Query("hot", enum=["hot", "new", "top"]),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Public feed — no auth required.
    Supports filtering by category/college and sorting by score, newest, or top.
    """
    q = db.query(Confession).filter(Confession.is_removed == False)

    if category:
        q = q.filter(Confession.category == category)
    if college_id:
        q = q.filter(Confession.college_id == college_id)

    if sort == "hot":
        q = q.order_by(Confession.score.desc(), Confession.created_at.desc())
    elif sort == "new":
        q = q.order_by(Confession.created_at.desc())
    elif sort == "top":
        q = q.order_by(Confession.upvotes.desc())

    return q.offset(skip).limit(limit).all()


# ── GET /confessions/{id} — Single confession ─────────────────────────────────

@router.get("/{confession_id}", response_model=ConfessionResponseSchema)
def get_confession(confession_id: UUID, db: Session = Depends(get_db)):
    confession = db.query(Confession).filter(
        Confession.id == confession_id, Confession.is_removed == False
    ).first()
    if not confession:
        raise HTTPException(status_code=404, detail="Confession not found.")
    return confession


# ── POST /confessions/{id}/vote — Vote on a confession ───────────────────────

@router.post("/{confession_id}/vote", summary="Upvote or downvote a confession")
def vote_confession(
    confession_id: UUID,
    payload: VoteSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    confession = db.query(Confession).filter(Confession.id == confession_id).first()
    if not confession:
        raise HTTPException(status_code=404, detail="Confession not found.")

    existing_vote = db.query(Vote).filter(
        Vote.user_id == current_user.id,
        Vote.confession_id == confession_id,
    ).first()

    vote_type = VoteType(payload.vote_type)

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Same vote again → remove vote (toggle off)
            db.delete(existing_vote)
            if vote_type == VoteType.up:
                confession.upvotes = max(0, confession.upvotes - 1)
            else:
                confession.downvotes = max(0, confession.downvotes - 1)
        else:
            # Switching vote direction
            existing_vote.vote_type = vote_type
            if vote_type == VoteType.up:
                confession.upvotes += 1
                confession.downvotes = max(0, confession.downvotes - 1)
            else:
                confession.downvotes += 1
                confession.upvotes = max(0, confession.upvotes - 1)
    else:
        new_vote = Vote(user_id=current_user.id, confession_id=confession_id, vote_type=vote_type)
        db.add(new_vote)
        if vote_type == VoteType.up:
            confession.upvotes += 1
        else:
            confession.downvotes += 1

    confession.score = confession.upvotes - confession.downvotes
    db.commit()
    return {"score": confession.score, "upvotes": confession.upvotes, "downvotes": confession.downvotes}


# ── POST /confessions/{id}/report — Report a confession ──────────────────────

@router.post("/{confession_id}/report", status_code=status.HTTP_201_CREATED)
def report_confession(
    confession_id: UUID,
    reason: ReportReason,
    description: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    confession = db.query(Confession).filter(Confession.id == confession_id).first()
    if not confession:
        raise HTTPException(status_code=404, detail="Confession not found.")

    report = Report(
        reporter_id=current_user.id,
        target_type="confession",
        target_id=confession_id,
        reason=reason,
        description=description,
    )
    db.add(report)

    # Auto-flag if report threshold reached
    report_count = db.query(Report).filter(Report.target_id == confession_id).count()
    if report_count >= 5:
        confession.is_flagged = True

    db.commit()
    return {"message": "Reported successfully. Our moderation team will review it."}
