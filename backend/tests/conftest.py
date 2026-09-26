import os

import pytest

# Refuse to run against anything that is not a throwaway database: the local
# guard is the database-name suffix, and CI's disposable service container is
# accepted explicitly (its URL is .../civicpulse, no suffix).
_db = os.environ.get("DATABASE_URL", "").rsplit("/", 1)[-1]
if not (_db.endswith("_test") or os.environ.get("GITHUB_ACTIONS") == "true"):
    pytest.exit("DATABASE_URL must point at a database whose name ends in _test", returncode=2)
os.environ.setdefault("REDIS_URL", "redis://unused:6379/0")
os.environ["TRIAGE_PROVIDER"] = "simulated"

try:
    import fakeredis
except ImportError:
    # CI installs only pytest/pytest-cov/httpx and provides a real Redis
    # service container, so the suite must not require fakeredis.
    fakeredis = None

from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from app.deps import get_engine, get_redis
from app.main import app

VALID = {
    "text": "Burst water main flooding Street 12, water entering ground floors",
    "location": "Street 12, Model Town",
}


@pytest.fixture(scope="session", autouse=True)
def migrated():
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(scope="session")
def backing_redis():
    if fakeredis is not None:
        return fakeredis.FakeRedis(decode_responses=True)
    # No fakeredis (CI): get_redis() bypasses dependency overrides and returns a
    # real client pointed at the job's Redis service container.
    return get_redis()


@pytest.fixture(autouse=True)
def clean_tables(backing_redis):
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE complaints"))
    backing_redis.flushdb()
    yield


@pytest.fixture
def client(backing_redis):
    app.dependency_overrides[get_redis] = lambda: backing_redis
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
