import os
import redis

_redis: redis.Redis | None = None


def init_cache() -> redis.Redis:
    global _redis
    _redis = redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True,
    )
    return _redis


def get_cache() -> redis.Redis | None:
    return _redis
