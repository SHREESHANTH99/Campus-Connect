from __future__ import annotations

from typing import Callable
from datetime import datetime, timedelta

import redis
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.deps import get_current_user_optional
from app.models.user import User

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
_memory_counters: dict[str, tuple[int, datetime]] = {}


def _identity(request: Request, user: User | None) -> str:
    if user:
        return f"user:{user.id}"
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def limiter(action: str, limit: int, window_seconds: int) -> Callable:
    async def _dep(request: Request, user: User | None = Depends(get_current_user_optional)) -> None:
        key = f"rl:{action}:{_identity(request, user)}"
        try:
            current = _redis.incr(key)
            if current == 1:
                _redis.expire(key, window_seconds)
            if current > limit:
                retry_after = max(_redis.ttl(key), 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {action}. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except Exception:
            if settings.REDIS_STRICT_MODE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Redis unavailable and strict mode is enabled.",
                )

            now = datetime.utcnow()
            count, expires_at = _memory_counters.get(key, (0, now + timedelta(seconds=window_seconds)))
            if now >= expires_at:
                count = 0
                expires_at = now + timedelta(seconds=window_seconds)
            count += 1
            _memory_counters[key] = (count, expires_at)

            if count > limit:
                retry_after = max(1, int((expires_at - now).total_seconds()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for {action}. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )

    return _dep
