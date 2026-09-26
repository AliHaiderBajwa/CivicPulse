from functools import lru_cache

from redis import Redis
from sqlalchemy import Engine, create_engine

from app.config import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Values come from the environment by design (required, no defaults), which
    # mypy cannot see — hence the ignore.
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)
