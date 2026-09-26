from enum import Enum

from app.domain import Category, Priority, Status
from app.providers.cache import Cache
from app.repositories.complaint_repository import ComplaintRepository
from app.repositories.models import Complaint

STATS_KEY = "stats:v1"


class StatsService:
    def __init__(self, repo: ComplaintRepository, cache: Cache, ttl_s: int) -> None:
        self._repo, self._cache, self._ttl = repo, cache, ttl_s

    def get(self) -> tuple[dict, bool]:
        cached = self._cache.get_json(STATS_KEY)
        if cached is not None:
            return cached, True                           # X-Cache: HIT
        data = self._compute()
        self._cache.set_json(STATS_KEY, data, self._ttl)  # TTL 30 s
        return data, False                                # X-Cache: MISS

    def invalidate(self) -> None:
        self._cache.delete(STATS_KEY)

    def _compute(self) -> dict:
        def fill(enum_cls: type[Enum], counts: dict[str, int]) -> dict[str, int]:
            # __members__.values(): iterates explicitly (Sonar S5864) and zero-fills
            # every enum value, including ones absent from the result set.
            return {m.value: counts.get(m.value, 0) for m in enum_cls.__members__.values()}
        return {
            "total": self._repo.total(),
            "by_category": fill(Category, self._repo.counts(Complaint.category)),
            "by_priority": fill(Priority, self._repo.counts(Complaint.priority)),
            "by_status": fill(Status, self._repo.counts(Complaint.status)),
        }
