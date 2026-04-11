from __future__ import annotations

import json

import redis

from app.core.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

CACHE_TTLS = {
    "trending_feed": 300,
    "hot_feed": 120,
    "event": 600,
    "club_members": 300,
    "user_karma": 60,
}


def _handle_redis_failure(exc: Exception) -> None:
    if settings.REDIS_STRICT_MODE:
        raise RuntimeError("Redis unavailable and strict mode is enabled for cache operations") from exc


def _safe_get(key: str):
    try:
        value = _redis.get(key)
        return json.loads(value) if value else None
    except Exception as exc:
        _handle_redis_failure(exc)
        return None


def _safe_set(key: str, payload, ttl: int):
    try:
        _redis.setex(key, ttl, json.dumps(payload))
    except Exception as exc:
        _handle_redis_failure(exc)
        return


def _safe_delete(*keys: str):
    if not keys:
        return
    try:
        _redis.delete(*keys)
    except Exception as exc:
        _handle_redis_failure(exc)
        return


def get_hot_feed(cursor: str | None, category: str | None, college_id: str | None, limit: int):
    key = f"feed:hot:{cursor or 'start'}:{category or 'all'}:{college_id or 'all'}:{limit}"
    return _safe_get(key)


def set_hot_feed(cursor: str | None, category: str | None, college_id: str | None, limit: int, payload):
    key = f"feed:hot:{cursor or 'start'}:{category or 'all'}:{college_id or 'all'}:{limit}"
    _safe_set(key, payload, CACHE_TTLS["hot_feed"])


def invalidate_hot_feed():
    try:
        keys = _redis.keys("feed:hot:*")
        if keys:
            _redis.delete(*keys)
    except Exception as exc:
        _handle_redis_failure(exc)
        return


def get_event(event_id: str):
    return _safe_get(f"event:{event_id}")


def set_event(event_id: str, payload):
    _safe_set(f"event:{event_id}", payload, CACHE_TTLS["event"])


def invalidate_event(event_id: str):
    _safe_delete(f"event:{event_id}")


def get_club_members(club_id: str, cursor: str | None, limit: int):
    return _safe_get(f"club:{club_id}:members:{cursor or 'start'}:{limit}")


def set_club_members(club_id: str, cursor: str | None, limit: int, payload):
    _safe_set(f"club:{club_id}:members:{cursor or 'start'}:{limit}", payload, CACHE_TTLS["club_members"])


def invalidate_club_members(club_id: str):
    try:
        keys = _redis.keys(f"club:{club_id}:members:*")
        if keys:
            _redis.delete(*keys)
    except Exception as exc:
        _handle_redis_failure(exc)
        return


def get_user_karma(user_id: str):
    return _safe_get(f"user:{user_id}:karma")


def set_user_karma(user_id: str, karma: int):
    _safe_set(f"user:{user_id}:karma", {"karma": karma}, CACHE_TTLS["user_karma"])


def invalidate_user_karma(user_id: str):
    _safe_delete(f"user:{user_id}:karma")
