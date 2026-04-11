from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.middleware.rate_limit import limiter
from app.models.poll import Poll, PollVote
from app.models.user import User
from app.schemas.poll import PollCreateSchema, PollResponseSchema, PollVoteSchema

router = APIRouter(prefix="/polls", tags=["Polls"])


@router.post("/", response_model=PollResponseSchema, status_code=status.HTTP_201_CREATED)
def create_poll(payload: PollCreateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    votes = {str(i): 0 for i in range(len(payload.options))}
    poll = Poll(
        question=payload.question,
        options=payload.options,
        votes=votes,
        creator_id=user.id,
        ends_at=payload.ends_at,
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)
    return poll


@router.get("/")
def list_polls(cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    q = db.query(Poll)
    if cursor:
        try:
            q = q.filter(Poll.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    rows = q.order_by(Poll.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1].created_at.isoformat() if has_more and rows else None
    return {"items": rows, "next_cursor": next_cursor, "has_more": has_more}


@router.get("/{poll_id}", response_model=PollResponseSchema)
def get_poll(poll_id: UUID, db: Session = Depends(get_db)):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


@router.post("/{poll_id}/vote", response_model=PollResponseSchema)
def vote_poll(
    poll_id: UUID,
    payload: PollVoteSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(limiter("poll_vote", limit=20, window_seconds=60)),
):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")

    if poll.ends_at and poll.ends_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Poll has ended")

    if payload.option_index >= len(poll.options):
        raise HTTPException(status_code=400, detail="Invalid option index")

    vote = db.query(PollVote).filter(PollVote.poll_id == poll_id, PollVote.user_id == user.id).first()
    votes = dict(poll.votes or {})

    if vote and vote.option_index == payload.option_index:
        return poll

    if vote:
        old_key = str(vote.option_index)
        votes[old_key] = max(0, int(votes.get(old_key, 0)) - 1)
        vote.option_index = payload.option_index
    else:
        vote = PollVote(poll_id=poll.id, user_id=user.id, option_index=payload.option_index)
        db.add(vote)
        poll.total_votes += 1

    new_key = str(payload.option_index)
    votes[new_key] = int(votes.get(new_key, 0)) + 1
    poll.votes = votes

    db.commit()
    db.refresh(poll)
    return poll


@router.get("/{poll_id}/results")
def poll_live_results(poll_id: UUID, db: Session = Depends(get_db)):
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return {
        "poll_id": str(poll.id),
        "votes": poll.votes,
        "total_votes": poll.total_votes,
        "server_time": datetime.utcnow().isoformat(),
    }
