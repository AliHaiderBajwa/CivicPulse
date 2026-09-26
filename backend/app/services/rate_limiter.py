from dataclasses import dataclass

from app.providers.cache import Cache


@dataclass(frozen=True)
class Decision:
    allowed: bool
    retry_after: int = 0


class RateLimiter:
    def __init__(self, cache: Cache, limit: int, window_s: int) -> None:
        self._cache, self._limit, self._window = cache, limit, window_s

    def check(self, client_id: str) -> Decision:
        result = self._cache.incr_window(f"ratelimit:complaints:{client_id}", self._window)
        if result is None:
            return Decision(True)  # fail open: limiter outage must not take down intake
        count, ttl = result
        return Decision(count <= self._limit, retry_after=ttl)
