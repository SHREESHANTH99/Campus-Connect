from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_current_user
from app.db.session import get_db
from app.middleware.rate_limit import limiter
from app.models.event import Event, EventRSVP, EventRSVPStatus
from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from app.services import cache_service
from app.schemas.event import EventCreateSchema, EventResponseSchema, EventUpdateSchema, RSVPResponseSchema

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventResponseSchema, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in (UserRole.organizer, UserRole.club_admin):
        raise HTTPException(status_code=403, detail="Organizer or club admin role required")

    event = Event(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        location=payload.location,
        organizer_id=user.id,
        club_id=payload.club_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        capacity=payload.capacity,
        is_public=payload.is_public,
        allow_waitlist=payload.allow_waitlist,
        banner_url=payload.banner_url,
        tags=payload.tags,
        schedule=payload.schedule,
        speakers=payload.speakers,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    if payload.club_id:
        cache_service.invalidate_club_members(str(payload.club_id))
    return event


@router.get("/", response_model=list[EventResponseSchema])
def list_events(
    category: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("upcoming"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(Event).filter(Event.is_cancelled == False)

    if category:
        q = q.filter(Event.category == category)
    if search:
        q = q.filter(Event.title.ilike(f"%{search}%"))
    if cursor:
        try:
            q = q.filter(Event.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")

    if sort == "new":
        q = q.order_by(Event.created_at.desc())
    else:
        q = q.order_by(Event.start_time.asc())

    return q.limit(limit).all()


@router.get("/{event_id}", response_model=EventResponseSchema)
def get_event(event_id: UUID, db: Session = Depends(get_db)):
    cached = cache_service.get_event(str(event_id))
    if cached:
        return cached

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    cache_service.set_event(
        str(event.id),
        {
            "id": str(event.id),
            "title": event.title,
            "description": event.description,
            "category": event.category,
            "location": event.location,
            "organizer_id": str(event.organizer_id),
            "club_id": str(event.club_id) if event.club_id else None,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "capacity": event.capacity,
            "attendee_count": event.attendee_count,
            "is_public": event.is_public,
            "allow_waitlist": event.allow_waitlist,
            "banner_url": event.banner_url,
            "tags": event.tags,
            "schedule": event.schedule,
            "speakers": event.speakers,
            "created_at": event.created_at.isoformat(),
            "is_cancelled": event.is_cancelled,
        },
    )
    return event


@router.post("/{event_id}/rsvp", response_model=RSVPResponseSchema)
def toggle_rsvp(
    event_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(limiter("event_rsvp", limit=20, window_seconds=600)),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_cancelled == False).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = db.query(EventRSVP).filter(EventRSVP.event_id == event_id, EventRSVP.user_id == user.id).first()
    if existing:
        db.delete(existing)
        event.attendee_count = max(0, event.attendee_count - 1)
        db.commit()
        cache_service.invalidate_event(str(event_id))
        return RSVPResponseSchema(attending=False, attendee_count=event.attendee_count, status=None)

    status_value = EventRSVPStatus.going
    if event.capacity and event.attendee_count >= event.capacity:
        if not event.allow_waitlist:
            raise HTTPException(status_code=400, detail="Event capacity reached")
        status_value = EventRSVPStatus.waitlist

    rsvp = EventRSVP(event_id=event.id, user_id=user.id, status=status_value)
    db.add(rsvp)
    if status_value == EventRSVPStatus.going:
        event.attendee_count += 1

    db.add(Notification(
        recipient_id=event.organizer_id,
        type=NotificationType.rsvp,
        title="New RSVP",
        message=f"{user.anonymous_username} RSVP'd to {event.title}",
        related_id=event.id,
        related_type="event",
    ))

    db.commit()
    cache_service.invalidate_event(str(event_id))
    return RSVPResponseSchema(attending=True, attendee_count=event.attendee_count, status=status_value)


@router.get("/{event_id}/attendees")
def list_attendees(event_id: UUID, cursor: str | None = Query(None), limit: int = Query(20, ge=1, le=50), db: Session = Depends(get_db)):
    total = db.query(func.count(EventRSVP.id)).filter(EventRSVP.event_id == event_id).scalar() or 0
    q = db.query(EventRSVP, User).join(User, User.id == EventRSVP.user_id).filter(EventRSVP.event_id == event_id)
    if cursor:
        try:
            q = q.filter(EventRSVP.created_at < datetime.fromisoformat(cursor))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor")
    rows = q.order_by(EventRSVP.created_at.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        {
            "user_id": str(user.id),
            "anonymous_username": user.anonymous_username,
            "status": rsvp.status.value,
            "joined_at": rsvp.created_at.isoformat(),
        }
        for rsvp, user in rows
    ]
    next_cursor = items[-1]["joined_at"] if has_more and items else None
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}


@router.put("/{event_id}", response_model=EventResponseSchema)
def update_event(event_id: UUID, payload: EventUpdateSchema, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the event owner can update this event")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    cache_service.invalidate_event(str(event_id))
    return event


@router.delete("/{event_id}")
def cancel_event(event_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only the event owner can cancel this event")

    event.is_cancelled = True
    db.commit()
    cache_service.invalidate_event(str(event_id))
    return {"message": "Event cancelled"}


@router.post("/{event_id}/transfer-ownership")
def transfer_event_ownership(
    event_id: UUID,
    new_owner_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Only current owner can transfer ownership")

    target = db.query(User).filter(User.id == new_owner_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="New owner user not found")

    event.organizer_id = target.id
    db.commit()
    cache_service.invalidate_event(str(event_id))
    return {"message": "Event ownership transferred", "new_owner_id": str(target.id)}
