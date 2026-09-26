from app.config import Settings
from app.providers.triage.factory import build_provider


def _settings(provider: str) -> Settings:
    return Settings(
        database_url="postgresql+psycopg://civicpulse:x@database:5432/civicpulse",
        redis_url="redis://cache:6379/0",
        triage_provider=provider,
    )


def test_meta_reports_active_provider_and_recent_outcomes(client):
    assert client.post("/api/complaints", json={
        "text": "Burst water main flooding Street 12",
        "location": "Street 12",
    }).status_code == 201

    r = client.get("/api/meta/providers")
    assert r.status_code == 200
    body = r.json()
    assert body["active_provider"] == "simulated"
    assert len(body["recent_triages"]) >= 1
    assert body["recent_triages"][0]["provider"] == "simulated"
    assert body["recent_triages"][0]["latency_ms"] >= 0


def test_meta_recent_triages_is_empty_without_traffic(client):
    r = client.get("/api/meta/providers")
    assert r.status_code == 200
    assert r.json()["recent_triages"] == []


def test_factory_builds_every_configured_provider():
    expectations = {
        "rules": ("RuleBasedTriage", "rules"),
        "simulated": ("SimulatedTriage", "simulated"),
        "llm": ("LLMTriage", "llm:groq"),
        "ollama": ("OllamaTriage", "llm:ollama"),
    }
    for configured, (class_name, runtime_name) in expectations.items():
        provider = build_provider(_settings(configured))
        assert type(provider).__name__ == class_name
        assert provider.name == runtime_name
