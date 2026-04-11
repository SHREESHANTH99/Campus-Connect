# Campus Connect

Anonymous, campus-first social platform built for students.

Campus Connect combines confessions, events, clubs, polls, profile systems, and realtime chat into one developer-friendly full-stack project.

## Why Developers Like This Repo

- Real product domain with clear user value and growth potential.
- Modern stack: Next.js frontend + FastAPI backend + PostgreSQL + Redis.
- End-to-end architecture already in place and actively evolving.
- Good contribution surface for frontend, backend, infra, and product experimentation.
- Built-in integration smoke tests to ship changes with confidence.

## What Is Already Built

### Backend (FastAPI)

- OTP login flow with JWT auth.
- Anonymous confessions feed:
	- create, vote, react, comment, report
	- hot/trending support
- Polls:
	- create, list with pagination shape, vote, live results endpoint
- Events:
	- create/list/get/update/cancel
	- RSVP and attendees pagination
	- ownership transfer endpoint
- Clubs:
	- create/list/get/update
	- join/leave toggle
	- members pagination
	- lead transfer endpoint
- Notifications:
	- list + mark as read
- Profile:
	- read/update self profile
	- role update endpoint (admin-gated)
- Search:
	- full-text style search across confessions, events, clubs
	- fallback behavior when full-text query path fails
- Caching strategy:
	- hot feed, event details, club members, user karma
- Rate limiting middleware:
	- endpoint-specific limits
	- Redis-first with configurable strict fail-fast mode
- Moderation service:
	- confession/comment moderation aligned to shared thresholds

### Frontend (Next.js)

- 3D-driven landing experience aligned with custom UI components.
- App routes for auth, dashboard, confessions, polls, events, clubs, chat, profile, notifications, settings, leaderboard.
- API client wired to backend endpoints for major Phase 3 flows.
- Confessions interaction UX with cards/modals/feed components.

### Infrastructure and DevOps

- Docker Compose setup for PostgreSQL + Redis + app services.
- Alembic migrations with current schema evolution through Phase 3 tables.
- Smoke tests for key integration behaviors.

## Current Architecture

| Layer | Tech |
|---|---|
| Frontend | Next.js (App Router), TypeScript |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Cache / Rate Limit | Redis |
| Auth | Phone OTP + JWT |
| Realtime | WebSocket chat module |
| Background Jobs | Celery scaffolding |

## Quick Start

### 1. Clone

```bash
git clone <your-repo-url>
cd campus-connect
```

### 2. Start Core Services

```bash
docker-compose up -d postgres redis
```

### 3. Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Run Frontend

```bash
cd ../frontend
npm install
npm run dev
```

### 5. Open App

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Local Testing

Run backend smoke tests:

```bash
cd backend
python tests/integration/smoke_phase3.py
```

## Project Structure

```text
campus-connect/
	backend/
		app/
			api/
			core/
			db/
			middleware/
			models/
			schemas/
			services/
			websockets/
			workers/
		alembic/
		tests/
	frontend/
		src/
			app/
			components/
			hooks/
			lib/
			store/
```

## Contribution Opportunities

High-impact areas open right now:

- Better recommendation logic for confessions/events/clubs.
- Improved chat matching and moderation hardening.
- Frontend UX polish for events, clubs, and profile flows.
- More tests: unit, API contract, and E2E.
- Container optimization and CI workflow setup.

## Roadmap Snapshot

- Done: core anonymous social primitives (auth, confessions, polls, events, clubs, notifications, search).
- In progress: deeper realtime interactions + stronger moderation/anti-abuse tooling.
- Next: recommendation engine, analytics, production-grade observability, and contributor tooling.

## How To Contribute

1. Fork and create a feature branch.
2. Keep changes focused and include tests when applicable.
3. Open a PR with:
	 - What changed
	 - Why it matters
	 - Screenshots or API examples if relevant
4. Be respectful in code review and document non-obvious decisions.

## Vision

Campus Connect aims to be the default anonymous social layer for student communities: safe, engaging, and deeply campus-native.

If you enjoy building products that blend social UX, realtime systems, and moderation challenges, this is a great place to contribute.
