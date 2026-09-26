from app.deps import get_provider
from app.main import app
from tests.conftest import VALID
from tests.doubles import AlwaysRaises, CountingProvider, FlakyProvider


def test_stats_miss_then_hit(client):
    first = client.get("/api/stats")
    assert first.headers["x-cache"] == "MISS"
    second = client.get("/api/stats")
    assert second.headers["x-cache"] == "HIT"
    assert first.json() == second.json()


def test_stats_invalidated_on_write(client):
    assert client.get("/api/stats").headers["x-cache"] == "MISS"
    assert client.post("/api/complaints", json=VALID).status_code == 201
    after_write = client.get("/api/stats")
    assert after_write.headers["x-cache"] == "MISS"
    assert after_write.json()["total"] == 1


def test_triage_cache_serves_duplicates(client):
    provider = CountingProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    first = client.post("/api/complaints", json=VALID)
    second = client.post("/api/complaints", json=VALID)
    assert first.status_code == 201 and second.status_code == 201
    assert provider.calls == 1  # identical text: one provider call, one cache hit
    assert first.json()["triaged_by"] == "simulated"
    assert second.json()["triaged_by"] == "simulated"


def test_fallback_result_is_not_cached(client):
    provider = FlakyProvider()
    app.dependency_overrides[get_provider] = lambda: provider
    first = client.post("/api/complaints", json=VALID)
    assert first.status_code == 201
    assert first.json()["triaged_by"] == "rules:fallback"
    second = client.post("/api/complaints", json=VALID)
    assert second.status_code == 201
    assert provider.calls == 2  # the outage's fallback answer was never cached
    assert second.json()["triaged_by"] == "simulated"


def test_provider_failure_never_leaks_a_500(client):
    app.dependency_overrides[get_provider] = lambda: AlwaysRaises()
    r = client.post("/api/complaints", json=VALID)
    assert r.status_code == 201
    assert r.json()["triaged_by"] == "rules:fallback"
