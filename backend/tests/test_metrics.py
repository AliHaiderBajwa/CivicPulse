import os

from app.config import Settings
from app.deps import get_provider, get_settings
from app.main import app
from tests.conftest import VALID
from tests.doubles import AlwaysRaises


def _fallback_total(text: str) -> float:
    total = 0.0
    for line in text.splitlines():
        if line.startswith("triage_fallback_total{"):
            total += float(line.rsplit(" ", 1)[1])
    return total


def test_metrics_exposes_the_documented_series(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.text.startswith("# HELP")
    for name in ("http_requests_total", "triage_fallback_total", "triage_cache_total"):
        assert f"# HELP {name}" in r.text
        assert f"# TYPE {name} counter" in r.text


def test_metrics_exposes_both_latency_histograms(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    for name in ("http_request_duration_seconds", "triage_duration_seconds"):
        assert f"# TYPE {name} histogram" in r.text
        assert f"{name}_bucket{{" in r.text
        assert f"{name}_sum" in r.text


def test_fallback_counter_increments_exactly_once_per_degradation(client):
    app.dependency_overrides[get_provider] = lambda: AlwaysRaises()
    try:
        before = _fallback_total(client.get("/metrics").text)
        r = client.post("/api/complaints", json=VALID)
    finally:
        app.dependency_overrides.pop(get_provider, None)

    assert r.status_code == 201  # the citizen never sees the provider failure
    assert r.json()["triaged_by"] == "rules:fallback"
    after = _fallback_total(client.get("/metrics").text)
    assert after == before + 1  # exactly one increment for exactly one fallback


def test_metrics_is_served_after_the_post_limiter_returns_429(client):
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url=os.environ["DATABASE_URL"],
        redis_url=os.environ["REDIS_URL"],
        rate_limit_per_min=2,
    )
    try:
        assert client.post("/api/complaints", json=VALID).status_code == 201
        assert client.post("/api/complaints", json=VALID).status_code == 201
        blocked = client.post("/api/complaints", json=VALID)
        r = client.get("/metrics")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert blocked.status_code == 429  # quota exhausted on the intake route
    assert r.status_code == 200  # /metrics is not behind that limiter
    assert "# TYPE http_requests_total counter" in r.text


def test_metrics_counts_requests_per_route(client):
    before = client.get("/metrics").text
    client.get("/api/stats")
    after = client.get("/metrics").text
    assert after != before  # the counter moved
