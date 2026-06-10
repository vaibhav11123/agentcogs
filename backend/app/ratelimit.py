"""Fixed-window rate limiting with Redis INCR + EXPIRE NX."""
from __future__ import annotations

import logging
import time

import redis as redis_lib

log = logging.getLogger("agentcogs.ratelimit")

_warn_last: dict[str, float] = {}


def _warn_once(key: str, msg: str) -> None:
    now = time.monotonic()
    if now - _warn_last.get(key, 0) >= 60:
        _warn_last[key] = now
        log.warning(msg)


async def check_rate(redis_client, bucket: str, limit: int, window_s: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds). Fail-open when Redis errors."""
    try:
        count = await redis_client.incr(bucket)
        if count == 1:
            await redis_client.expire(bucket, window_s)
        ttl = await redis_client.ttl(bucket)
        if ttl < 0:
            ttl = window_s
        if count > limit:
            return False, max(1, int(ttl))
        return True, 0
    except (redis_lib.exceptions.RedisError, OSError) as e:
        _warn_once("ratelimit", f"rate limit check failed, allowing request: {e}")
        return True, 0
