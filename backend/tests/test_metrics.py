def test_metrics_exposes_the_documented_series(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.text.startswith("# HELP")
    for name in ("http_requests_total", "triage_fallback_total", "triage_cache_total"):
        assert f"# HELP {name}" in r.text
        assert f"# TYPE {name} counter" in r.text


def test_metrics_counts_requests_per_route(client):
    before = client.get("/metrics").text
    client.get("/api/stats")
    after = client.get("/metrics").text
    assert after != before  # the counter moved
