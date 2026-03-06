# app/services/auth_service.py

import random
import uuid
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_phone


# ── Anonymous username generator ─────────────────────────────────────────────

_ADJECTIVES = [
    "Shadow", "Neon", "Cosmic", "Silent", "Blazing", "Quantum",
    "Stealthy", "Turbo", "Phantom", "Rogue", "Electric", "Mystic",
]
_ANIMALS = [
    "Panda", "Tiger", "Falcon", "Shark", "Wolf", "Phoenix",
    "Dragon", "Cobra", "Raven", "Otter", "Lynx", "Jaguar",
]


def _generate_anonymous_username() -> str:
    adj = random.choice(_ADJECTIVES)
    animal = random.choice(_ANIMALS)
    number = random.randint(1000, 9999)
    return f"{adj}_{animal}_{number}"


# ── Core auth operations ──────────────────────────────────────────────────────

def get_user_by_phone_hash(db: Session, phone_hash: str) -> User | None:
    return db.query(User).filter(User.phone_hash == phone_hash).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_anonymous_user(db: Session, phone_hash: str) -> User:
    """
    Create a new anonymous user with a randomly generated username.
    Retries username generation if there's a collision (very rare).
    """
    for _ in range(5):
        username = _generate_anonymous_username()
        if not db.query(User).filter(User.anonymous_username == username).first():
            break

    user = User(phone_hash=phone_hash, anonymous_username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(db: Session, phone: str) -> tuple[User, bool]:
    """
    Look up user by hashed phone. Create if not found.
    Returns (user, created) where created=True means a new account was made.
    """
    phone_hash = hash_phone(phone)
    user = get_user_by_phone_hash(db, phone_hash)
    if user:
        return user, False
    user = create_anonymous_user(db, phone_hash)
    return user, True
