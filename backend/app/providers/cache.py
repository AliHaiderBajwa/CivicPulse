import json
import logging
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

log = logging.getLogger("app.cache")


class Cache:
    """Thin Redis wrapper. Cache failures degrade gracefully; they must never break a request."""

    def __init__(self, client: Redis) -> None:
        self._r = client

    def get_json(self, key: str) -> Any | None:
        try:
            raw = self._r.get(key)
            return json.loads(raw) if raw else None
        except (RedisError, ValueError):
            log.warning("cache read failed", extra={"cache_key": key})
            return None

    def set_json(self, key: str, value: Any, ttl_s: int) -> None:
        try:
            self._r.set(key, json.dumps(value), ex=ttl_s)
        except RedisError:
            log.warning("cache write failed", extra={"cache_key": key})

    def delete(self, key: str) -> None:
        try:
            self._r.delete(key)
        except RedisError:
            log.warning("cache delete failed", extra={"cache_key": key})

    def incr(self, key: str) -> None:
        try:
            self._r.incr(key)
        except RedisError:
            pass

    def push_recent(self, key: str, item: dict[str, Any], maxlen: int) -> None:
        try:
            pipe = self._r.pipeline()
            pipe.lpush(key, json.dumps(item))
            pipe.ltrim(key, 0, maxlen - 1)
            pipe.execute()
        except RedisError:
            pass

    def recent(self, key: str, n: int) -> list[dict[str, Any]]:
        try:
            return [json.loads(x) for x in self._r.lrange(key, 0, n - 1)]
        except (RedisError, ValueError):
            return []

    def incr_window(self, key: str, window_s: int) -> tuple[int, int] | None:
        """Fixed-window counter. Returns (count, seconds_left) or None if Redis is unavailable."""
        try:
            pipe = self._r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_s, nx=True)   # only set the TTL on the first hit of the window
            pipe.ttl(key)
            count, _, ttl = pipe.execute()
            return int(count), max(int(ttl), 1)
        except RedisError:
            return None

    def ping(self) -> bool:
        try:
            return bool(self._r.ping())
        except RedisError:
            return False
