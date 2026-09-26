import logging

from app.providers.cache import Cache
from app.repositories.complaint_repository import ComplaintRepository

log = logging.getLogger("app.health")


class HealthService:
    def __init__(self, repo: ComplaintRepository, cache: Cache) -> None:
        self._repo, self._cache = repo, cache

    def check(self) -> dict[str, bool]:
        state = {"postgres": False, "redis": False}
        try:
            self._repo.ping()
            state["postgres"] = True
        except Exception as exc:  # noqa: BLE001 — readiness reports any DB failure, not a few types
            log.debug("postgres unreachable during readiness", extra={"error_class": type(exc).__name__})
        state["redis"] = self._cache.ping()
        return state
