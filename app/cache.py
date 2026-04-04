import json
import os

import redis

_redis: redis.Redis | None = None

CACHE_TTL = 300  # 5 minutes for list/detail endpoints


def init_cache() -> redis.Redis:
    global _redis
    _redis = redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )
    return _redis


def get_cache() -> redis.Redis | None:
    return _redis


def cache_get(key: str):
    """Get a JSON-serialized value from cache. Returns None on miss or error."""
    c = get_cache()
    if not c:
        return None
    try:
        raw = c.get(key)
        if raw is not None:
            return json.loads(raw)
    except Exception:
        pass
    return None


def cache_set(key: str, value, ttl: int = CACHE_TTL):
    """Set a JSON-serialized value in cache."""
    c = get_cache()
    if not c:
        return
    try:
        c.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


def cache_delete_pattern(pattern: str):
    """Delete all keys matching a pattern (e.g. 'users:*')."""
    c = get_cache()
    if not c:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = c.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                c.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass


def cache_delete(key: str):
    """Delete a specific cache key."""
    c = get_cache()
    if not c:
        return
    try:
        c.delete(key)
    except Exception:
        pass
