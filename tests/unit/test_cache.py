"""Unit tests for app/cache.py — covers no-redis, cache-hit, and exception paths."""
import json
from unittest.mock import MagicMock

import app.cache as cache_module
from app.cache import cache_delete, cache_delete_pattern, cache_get, cache_set


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _NullRedis:
    """Context manager that temporarily sets _redis to None."""

    def __enter__(self):
        self._orig = cache_module._redis
        cache_module._redis = None
        return self

    def __exit__(self, *_):
        cache_module._redis = self._orig


class _MockRedis:
    """Context manager that installs a MagicMock as _redis."""

    def __init__(self, **side_effects):
        self._side_effects = side_effects

    def __enter__(self):
        self._orig = cache_module._redis
        self.mock = MagicMock()
        for attr, exc in self._side_effects.items():
            getattr(self.mock, attr).side_effect = exc
        cache_module._redis = self.mock
        return self.mock

    def __exit__(self, *_):
        cache_module._redis = self._orig


# ---------------------------------------------------------------------------
# cache_get — no redis
# ---------------------------------------------------------------------------

def test_cache_get_returns_none_when_redis_is_not_configured():
    with _NullRedis():
        assert cache_get("some_key") is None


# ---------------------------------------------------------------------------
# cache_get — cache hit
# ---------------------------------------------------------------------------

def test_cache_get_returns_deserialized_value_on_hit():
    with _MockRedis() as mock_r:
        mock_r.get.return_value = json.dumps({"result": [1, 2, 3]})
        assert cache_get("some_key") == {"result": [1, 2, 3]}


# ---------------------------------------------------------------------------
# cache_get — exception path
# ---------------------------------------------------------------------------

def test_cache_get_returns_none_on_redis_exception():
    with _MockRedis(get=Exception("connection lost")):
        assert cache_get("some_key") is None


# ---------------------------------------------------------------------------
# cache_set — no redis
# ---------------------------------------------------------------------------

def test_cache_set_does_not_raise_when_redis_is_not_configured():
    with _NullRedis():
        cache_set("some_key", {"data": 1})  # must not raise


# ---------------------------------------------------------------------------
# cache_set — exception path
# ---------------------------------------------------------------------------

def test_cache_set_silences_redis_exception():
    with _MockRedis(set=Exception("write failed")):
        cache_set("some_key", {"data": 1})  # must not raise


# ---------------------------------------------------------------------------
# cache_delete_pattern — no redis
# ---------------------------------------------------------------------------

def test_cache_delete_pattern_does_not_raise_when_redis_is_not_configured():
    with _NullRedis():
        cache_delete_pattern("users:*")  # must not raise


# ---------------------------------------------------------------------------
# cache_delete_pattern — exception path
# ---------------------------------------------------------------------------

def test_cache_delete_pattern_silences_redis_exception():
    with _MockRedis(scan=Exception("scan failed")):
        cache_delete_pattern("users:*")  # must not raise


# ---------------------------------------------------------------------------
# cache_delete — no redis
# ---------------------------------------------------------------------------

def test_cache_delete_does_not_raise_when_redis_is_not_configured():
    with _NullRedis():
        cache_delete("some_key")  # must not raise


# ---------------------------------------------------------------------------
# cache_delete — exception path
# ---------------------------------------------------------------------------

def test_cache_delete_silences_redis_exception():
    with _MockRedis(delete=Exception("delete failed")):
        cache_delete("some_key")  # must not raise
