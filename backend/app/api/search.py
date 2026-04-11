from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.club import Club
from app.models.confession import Confession
from app.models.event import Event

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/")
def full_text_search(
    q: str = Query(..., min_length=2, max_length=120),
    scope: str = Query("all", pattern="^(all|confessions|events|clubs)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    results = {"confessions": [], "events": [], "clubs": []}

    def include(name: str) -> bool:
        return scope in ("all", name)

    if include("confessions"):
        try:
            rows = (
                db.query(Confession)
                .filter(
                    Confession.is_removed == False,
                    func.to_tsvector("english", Confession.content).op("@@")(func.plainto_tsquery("english", q)),
                )
                .order_by(Confession.created_at.desc())
                .limit(limit)
                .all()
            )
        except Exception:
            rows = (
                db.query(Confession)
                .filter(Confession.is_removed == False, Confession.content.ilike(f"%{q}%"))
                .order_by(Confession.created_at.desc())
                .limit(limit)
                .all()
            )
        results["confessions"] = [
            {
                "id": str(r.id),
                "content": r.content,
                "category": r.category.value,
                "score": r.score,
                "created_at": r.created_at,
            }
            for r in rows
        ]

    if include("events"):
        try:
            rows = (
                db.query(Event)
                .filter(
                    Event.is_cancelled == False,
                    func.to_tsvector("english", Event.title + " " + Event.description).op("@@")(
                        func.plainto_tsquery("english", q)
                    ),
                )
                .order_by(Event.start_time.asc())
                .limit(limit)
                .all()
            )
        except Exception:
            rows = (
                db.query(Event)
                .filter(
                    Event.is_cancelled == False,
                    or_(Event.title.ilike(f"%{q}%"), Event.description.ilike(f"%{q}%")),
                )
                .order_by(Event.start_time.asc())
                .limit(limit)
                .all()
            )

        results["events"] = [
            {
                "id": str(r.id),
                "title": r.title,
                "category": r.category,
                "location": r.location,
                "start_time": r.start_time,
            }
            for r in rows
        ]

    if include("clubs"):
        try:
            rows = (
                db.query(Club)
                .filter(
                    func.to_tsvector("english", Club.name + " " + Club.description).op("@@")(
                        func.plainto_tsquery("english", q)
                    )
                )
                .order_by(Club.member_count.desc())
                .limit(limit)
                .all()
            )
        except Exception:
            rows = (
                db.query(Club)
                .filter(or_(Club.name.ilike(f"%{q}%"), Club.description.ilike(f"%{q}%")))
                .order_by(Club.member_count.desc())
                .limit(limit)
                .all()
            )

        results["clubs"] = [
            {
                "id": str(r.id),
                "name": r.name,
                "category": r.category,
                "member_count": r.member_count,
            }
            for r in rows
        ]

    return results
