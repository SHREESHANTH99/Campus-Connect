# app/core/deps.py

import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserStatus

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — validates JWT and returns the current User object.
    Raises 401 if token is invalid, 403 if user is banned.
    """
    token = credentials.credentials
    user_id_str = decode_access_token(token)

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    if user.status == UserStatus.banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account banned.")

    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Best-effort user extraction for rate limiting and telemetry."""
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None

    token = auth.split(" ", 1)[1].strip()
    user_id_str = decode_access_token(token)
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    return db.query(User).filter(User.id == user_id).first()
