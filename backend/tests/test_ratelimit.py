import os

from app.config import Settings
from app.deps import get_settings
from app.main import app
from tests.conftest import VALID


def test_third_post_is_429_with_retry_after(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url=os.environ["DATABASE_URL"],
        redis_url=os.environ["REDIS_URL"],
        rate_limit_per_min=2,
    )
    try:
        assert client.post("/api/complaints", json=VALID).status_code == 201
        assert client.post("/api/complaints", json=VALID).status_code == 201
        third = client.post("/api/complaints", json=VALID)
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert third.status_code == 429
    assert int(third.headers["retry-after"]) > 0
    assert third.json()["detail"]


def test_rate_limit_is_per_client_address(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url=os.environ["DATABASE_URL"],
        redis_url=os.environ["REDIS_URL"],
        rate_limit_per_min=2,
    )
    try:
        for _ in range(2):
            assert client.post("/api/complaints", json=VALID).status_code == 201
        blocked = client.post("/api/complaints", json=VALID)
        forwarded = client.post(
            "/api/complaints", json=VALID, headers={"X-Forwarded-For": "203.0.113.9"}
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert blocked.status_code == 429
    assert forwarded.status_code == 201  # a different client has its own window
