from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.club import Club, ClubMembership
from app.models.event import Event
from app.models.user import User, UserRole
from app.services import cache_service
from app.schemas.club import ClubCreateSchema, ClubJoinResponseSchema, ClubResponseSchema, ClubUpdateSchema

router = APIRouter(prefix="/clubs", tags=["Clubs"])


@router.post("/", response_model=ClubResponseSchema, status_code=status.HTTP_201_CREATED)
def create_club(payload: ClubCreateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in (UserRole.club_admin, UserRole.organizer):
        raise HTTPException(status_code=403, detail="Club admin or organizer role required")

    existing = db.query(Club).filter(Club.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Club name already exists")

    club = Club(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        logo_url=payload.logo_url,
        banner_url=payload.banner_url,
        lead_id=user.id,
        founded_year=payload.founded_year,
    )
    db.add(club)
    db.commit()
    db.refresh(club)
    return club


@router.get("/", response_model=list[ClubResponseSchema])
def list_clubs(category: str | None = Query(None), search: str | None = Query(None), limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)):
    q = db.query(Club)
    if category:
        q = q.filter(Club.category == category)
    if search:
        q = q.filter(Club.name.ilike(f"%{search}%"))
    return q.order_by(Club.member_count.desc(), Club.created_at.desc()).limit(limit).all()


@router.get("/{club_id}", response_model=ClubResponseSchema)
def get_club(club_id: UUID, db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.post("/{club_id}/join", response_model=ClubJoinResponseSchema)
def join_or_leave_club(club_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    membership = db.query(ClubMembership).filter(ClubMembership.club_id == club_id, ClubMembership.user_id == user.id).first()
    if membership:
        db.delete(membership)
        club.member_count = max(0, club.member_count - 1)
        db.commit()
        cache_service.invalidate_club_members(str(club_id))
        return ClubJoinResponseSchema(joined=False, member_count=club.member_count)

    db.add(ClubMembership(club_id=club_id, user_id=user.id))
    club.member_count += 1
    db.commit()
    cache_service.invalidate_club_members(str(club_id))
    return ClubJoinResponseSchema(joined=True, member_count=club.member_count)


@router.get("/{club_id}/members")
def list_members(club_id: UUID, cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    cached = cache_service.get_club_members(str(club_id), cursor=cursor, limit=limit)
    if cached:
        return cached

    total = db.query(func.count(ClubMembership.id)).filter(ClubMembership.club_id == club_id).scalar() or 0
    q = db.query(ClubMembership, User).join(User, User.id == ClubMembership.user_id).filter(ClubMembership.club_id == club_id)
    if cursor:
        try:
            q = q.filter(ClubMembership.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    rows = q.order_by(ClubMembership.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        {
            "user_id": str(user.id),
            "anonymous_username": user.anonymous_username,
            "joined_at": membership.created_at.isoformat(),
        }
        for membership, user in rows
    ]
    next_cursor = items[-1]["joined_at"] if has_more and items else None
    payload = {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}
    cache_service.set_club_members(str(club_id), cursor=cursor, limit=limit, payload=payload)
    return payload


@router.get("/{club_id}/events")
def club_events(club_id: UUID, limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    return db.query(Event).filter(Event.club_id == club_id, Event.is_cancelled == False).order_by(Event.start_time.asc()).limit(limit).all()


@router.put("/{club_id}", response_model=ClubResponseSchema)
def update_club(club_id: UUID, payload: ClubUpdateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    if club.lead_id != user.id:
        raise HTTPException(status_code=403, detail="Only the club lead can update this club")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(club, field, value)

    db.commit()
    db.refresh(club)
    return club


@router.post("/{club_id}/transfer-lead")
def transfer_club_lead(
    club_id: UUID,
    new_lead_user_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    if club.lead_id != user.id:
        raise HTTPException(status_code=403, detail="Only current lead can transfer ownership")

    target = db.query(User).filter(User.id == new_lead_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    club.lead_id = target.id
    db.commit()
    return {"message": "Club lead transferred", "new_lead_id": str(target.id)}
