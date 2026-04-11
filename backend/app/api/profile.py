from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.club import Club, ClubMembership
from app.models.confession import Confession
from app.models.event import Event, EventRSVP
from app.models.user import User, UserRole
from app.services import cache_service
from app.schemas.club import ClubResponseSchema
from app.schemas.confession import ConfessionResponseSchema
from app.schemas.event import EventResponseSchema
from app.schemas.profile import ProfileResponseSchema, ProfileUpdateSchema

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponseSchema)
def profile_me(user: User = Depends(get_current_user)):
    cached = cache_service.get_user_karma(str(user.id))
    if cached and "karma" in cached:
        user.karma = int(cached["karma"])
    else:
        cache_service.set_user_karma(str(user.id), int(user.karma))
    return user


@router.patch("/me", response_model=ProfileResponseSchema)
def update_profile(payload: ProfileUpdateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    cache_service.invalidate_user_karma(str(user.id))
    return user


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: UUID,
    role: UserRole,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != UserRole.club_admin:
        raise HTTPException(status_code=403, detail="Only club_admin can update user roles")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")

    target.role = role
    db.commit()
    return {"message": "Role updated", "user_id": str(target.id), "role": target.role.value}


@router.get("/me/confessions", response_model=list[ConfessionResponseSchema])
def my_confessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Confession).filter(Confession.author_id == user.id).order_by(Confession.created_at.desc()).all()


@router.get("/me/events", response_model=list[EventResponseSchema])
def my_events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Event)
        .join(EventRSVP, EventRSVP.event_id == Event.id)
        .filter(EventRSVP.user_id == user.id)
        .order_by(Event.start_time.asc())
        .all()
    )


@router.get("/me/clubs", response_model=list[ClubResponseSchema])
def my_clubs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Club)
        .join(ClubMembership, ClubMembership.club_id == Club.id)
        .filter(ClubMembership.user_id == user.id)
        .order_by(Club.member_count.desc())
        .all()
    )
