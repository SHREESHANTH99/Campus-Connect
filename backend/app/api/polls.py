# app/api/polls.py
# Phase 2 feature — router is registered now so the URL namespace is reserved.
# Full implementation (poll creation, voting, live debates) comes in Phase 2.

from fastapi import APIRouter

router = APIRouter(prefix="/polls", tags=["Polls"])


@router.get("/", summary="List polls (Phase 2)")
def list_polls():
    return {"message": "Polls are coming in Phase 2. Stay tuned!"}
