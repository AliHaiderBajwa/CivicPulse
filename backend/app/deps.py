from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.providers.cache import Cache
from app.providers.triage.base import TriageProvider
from app.providers.triage.factory import build_provider
from app.providers.triage.rules import RuleBasedTriage
from app.repositories.complaint_repository import ComplaintRepository
from app.services.complaint_service import ComplaintService
from app.services.health_service import HealthService
from app.services.meta_service import MetaService
from app.services.rate_limiter import RateLimiter
from app.services.stats_service import StatsService
from app.services.triage_orchestrator import TriageOrchestrator


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Values come from the environment by design (required, no defaults), which
    # mypy cannot see — hence the ignore.
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5,
                         max_overflow=5, connect_args={"connect_timeout": 3})


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with get_sessionmaker()() as session:      # closing rolls back anything uncommitted
        yield session


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True,
                          socket_timeout=2, socket_connect_timeout=2)


def get_cache(client: Annotated[Redis, Depends(get_redis)]) -> Cache:
    return Cache(client)


@lru_cache(maxsize=1)
def _provider_singleton() -> TriageProvider:
    return build_provider(get_settings())


def get_provider() -> TriageProvider:              # tests override this
    return _provider_singleton()


def get_repository(session: Annotated[Session, Depends(get_session)]) -> ComplaintRepository:
    return ComplaintRepository(session)


def get_stats_service(
    repo: Annotated[ComplaintRepository, Depends(get_repository)],
    cache: Annotated[Cache, Depends(get_cache)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StatsService:
    return StatsService(repo, cache, settings.stats_ttl_s)


def get_complaint_service(
    repo: Annotated[ComplaintRepository, Depends(get_repository)],
    cache: Annotated[Cache, Depends(get_cache)],
    provider: Annotated[TriageProvider, Depends(get_provider)],
    stats: Annotated[StatsService, Depends(get_stats_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComplaintService:
    triage = TriageOrchestrator(provider, RuleBasedTriage(), cache, settings.triage_cache_ttl_s)
    return ComplaintService(repo, triage, stats)


def get_rate_limiter(
    cache: Annotated[Cache, Depends(get_cache)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RateLimiter:
    return RateLimiter(cache, settings.rate_limit_per_min, window_s=60)


def get_health_service(
    repo: Annotated[ComplaintRepository, Depends(get_repository)],
    cache: Annotated[Cache, Depends(get_cache)],
) -> HealthService:
    return HealthService(repo, cache)


def get_meta_service(
    cache: Annotated[Cache, Depends(get_cache)],
    provider: Annotated[TriageProvider, Depends(get_provider)],
) -> MetaService:
    return MetaService(cache, provider)
