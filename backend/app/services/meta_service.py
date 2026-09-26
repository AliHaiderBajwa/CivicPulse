from app.providers.cache import Cache
from app.providers.triage.base import TriageProvider
from app.services.triage_orchestrator import OUTCOMES_KEY


class MetaService:
    def __init__(self, cache: Cache, provider: TriageProvider) -> None:
        self._cache, self._provider = cache, provider

    def providers(self) -> dict:
        return {"active": self._provider.name, "recent": self._cache.recent(OUTCOMES_KEY, 20)}
