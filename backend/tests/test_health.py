from redis import RedisError

from app.deps import get_redis, get_repository
from app.main import app


class DeadRepo:
    def ping(self):
        raise RuntimeError("database unreachable")


class DeadRedis:
    def ping(self):
        raise RedisError("redis unreachable")


def test_health_is_200_even_with_a_dead_database(client):
    app.dependency_overrides[get_repository] = lambda: DeadRepo()
    try:
        health = client.get("/health")
        ready = client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_repository, None)

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}  # liveness never touches the database
    assert ready.status_code == 503
    body = ready.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgres"] is False
    assert body["dependencies"]["redis"] is True


def test_ready_is_503_when_redis_is_down(client):
    app.dependency_overrides[get_redis] = lambda: DeadRedis()
    try:
        ready = client.get("/ready")
    finally:
        app.dependency_overrides.pop(get_redis, None)

    assert ready.status_code == 503
    body = ready.json()
    assert body["dependencies"]["redis"] is False
    assert body["dependencies"]["postgres"] is True


def test_ready_is_200_when_everything_is_up(client):
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ok", "dependencies": {"postgres": True, "redis": True}}
