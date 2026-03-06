# app/api/chat.py

from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.chat_session import ChatSession, ChatMode, ChatSessionStatus
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── POST /chat/join — Join matchmaking queue ──────────────────────────────────

@router.post("/join", summary="Join random chat queue")
def join_chat(
    mode: str = "fun",
    college_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1: User requests to be matched.
    - Checks if a waiting session exists with matching mode/college filter
    - If yes: pairs users, sets session to active
    - If no: creates a new waiting session for this user
    Real-time matching signals are sent via WebSocket (see websockets/).
    """
    try:
        chat_mode = ChatMode(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Use fun/study/vent.")

    college_id = current_user.college_id if college_only else None

    # Look for a waiting session we can join
    waiting_q = db.query(ChatSession).filter(
        ChatSession.status == ChatSessionStatus.waiting,
        ChatSession.mode == chat_mode,
        ChatSession.user_a_id != current_user.id,
    )
    if college_id:
        waiting_q = waiting_q.filter(ChatSession.college_id == college_id)

    waiting_session = waiting_q.first()

    if waiting_session:
        # Pair the two users
        waiting_session.user_b_id = current_user.id
        waiting_session.status = ChatSessionStatus.active
        db.commit()
        db.refresh(waiting_session)
        return {
            "session_id": str(waiting_session.id),
            "status": "matched",
            "mode": chat_mode.value,
            "message": "You've been matched! Start chatting.",
        }

    # No waiting session — create one
    new_session = ChatSession(
        user_a_id=current_user.id,
        mode=chat_mode,
        college_id=college_id,
        status=ChatSessionStatus.waiting,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {
        "session_id": str(new_session.id),
        "status": "waiting",
        "mode": chat_mode.value,
        "message": "Looking for a match... connect via WebSocket to receive updates.",
    }


# ── POST /chat/{session_id}/end — End a session ───────────────────────────────

@router.post("/{session_id}/end", summary="End a chat session")
def end_chat(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Marks the session as ended.
    Messages are never stored — only metadata is updated here.
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if current_user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="You are not part of this session.")

    session.status = ChatSessionStatus.ended
    session.ended_at = datetime.utcnow()
    session.messages_wiped = True   # confirm no messages stored
    db.commit()

    return {"message": "Session ended. No messages were stored."}


# ── GET /chat/{session_id} — Session info ────────────────────────────────────

@router.get("/{session_id}", summary="Get chat session metadata")
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if current_user.id not in (session.user_a_id, session.user_b_id):
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "session_id": str(session.id),
        "mode": session.mode.value,
        "status": session.status.value,
        "created_at": session.created_at,
        "ended_at": session.ended_at,
    }
