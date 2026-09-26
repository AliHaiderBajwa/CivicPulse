import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from app.metrics import TRIAGE_CACHE, TRIAGE_FALLBACKS, TRIAGE_LATENCY
from app.providers.cache import Cache
from app.providers.triage.base import TriageProvider, TriageResult
from app.services.redaction import redact

log = logging.getLogger("app.triage")
OUTCOMES_KEY = "triage:outcomes"


@dataclass(frozen=True)
class TriageOutcome:
    result: TriageResult
    triaged_by: str
    latency_ms: int
    fallback: bool
    cached: bool
    error_class: str | None = None


def content_key(provider_name: str, safe_text: str) -> str:
    normalised = " ".join(safe_text.lower().split())
    return f"triage:v1:{provider_name}:{hashlib.sha256(normalised.encode()).hexdigest()}"


class TriageOrchestrator:
    def __init__(
        self, primary: TriageProvider, fallback: TriageProvider, cache: Cache, ttl_s: int
    ) -> None:
        self._primary, self._fallback, self._cache, self._ttl = primary, fallback, cache, ttl_s

    @property
    def primary_name(self) -> str:
        return self._primary.name

    def run(self, text: str, location: str) -> TriageOutcome:
        safe = redact(text)                      # only redacted body ever goes to a provider
        key = content_key(self._primary.name, safe)  # text-only: one call per text
        started = time.perf_counter()

        hit = self._cache.get_json(key)
        if hit is not None:
            try:
                result = TriageResult.model_validate(hit["result"])
                TRIAGE_CACHE.labels("hit").inc()
                self._cache.incr("triage:cache:hit")
                outcome = TriageOutcome(result, hit["triaged_by"], self._ms(started), False, True)
                self._record(outcome)
                return outcome
            except Exception:  # noqa: BLE001 — corrupt entry of any shape is a cache miss
                log.warning("corrupt triage cache entry", extra={"cache_key": key})
        TRIAGE_CACHE.labels("miss").inc()
        self._cache.incr("triage:cache:miss")

        try:
            result = self._primary.triage(safe, location)
            triaged_by, fallback, error_class = self._primary.name, False, None
            # Only successful primary results are cached; caching a fallback would pin a
            # temporary outage's low-quality answer for 24 hours.
            self._cache.set_json(key, {"result": result.model_dump(mode="json"),
                                       "triaged_by": triaged_by}, self._ttl)
        except Exception as exc:  # noqa: BLE001 — ANY provider failure: the citizen must never see a 500
            result = self._fallback.triage(text, location)
            triaged_by, fallback = "rules:fallback", True
            error_class = type(exc.__cause__ or exc).__name__
            TRIAGE_FALLBACKS.labels(self._primary.name, error_class).inc()

        latency = self._ms(started)
        TRIAGE_LATENCY.labels(triaged_by).observe(latency / 1000)
        outcome = TriageOutcome(result, triaged_by, latency, fallback, False, error_class)
        self._record(outcome)
        return outcome

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    def _record(self, o: TriageOutcome) -> None:
        self._cache.push_recent(OUTCOMES_KEY, {
            "provider": o.triaged_by, "latency_ms": o.latency_ms, "fallback": o.fallback,
            "cached": o.cached, "at": datetime.now(UTC).isoformat(),
        }, maxlen=20)
