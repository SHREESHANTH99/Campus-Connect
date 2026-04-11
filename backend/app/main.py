# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, confessions, chat, polls, events, clubs, notifications, profile, search
from app.core.config import settings

app = FastAPI(
    title="Campus Connect API",
    description="Anonymous social hub for engineering students — Phase 3",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Adjust origins for production — lock down to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API routers ──────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api")
app.include_router(confessions.router, prefix="/api")
app.include_router(chat.router,        prefix="/api")
app.include_router(polls.router,       prefix="/api")
app.include_router(events.router,      prefix="/api")
app.include_router(clubs.router,       prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(profile.router,     prefix="/api")
app.include_router(search.router,      prefix="/api")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "Campus Connect API"}


# ── Final URL map ─────────────────────────────────────────────────────────────
# POST   /api/auth/request-otp
# POST   /api/auth/verify-otp
# GET    /api/auth/me
#
# POST   /api/confessions/
# GET    /api/confessions/
# GET    /api/confessions/{id}
# POST   /api/confessions/{id}/vote
# POST   /api/confessions/{id}/report
#
# POST   /api/chat/join
# GET    /api/chat/{session_id}
# POST   /api/chat/{session_id}/end
#
# GET    /api/polls/          ← Phase 2 stub
