# app/db/base.py
# Import this everywhere models need Base, so Alembic can discover all tables.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# ── Import all models here so Alembic autogenerate sees them ─────────────────
from app.models.user import User              # noqa: F401, E402
from app.models.confession import Confession  # noqa: F401, E402
from app.models.vote import Vote              # noqa: F401, E402
from app.models.report import Report          # noqa: F401, E402
from app.models.chat_session import ChatSession  # noqa: F401, E402
