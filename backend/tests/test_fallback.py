from app.deps import get_provider
from app.main import app
from tests.conftest import VALID
from tests.doubles import AlwaysRaises


def test_provider_failure_still_returns_201_and_falls_back(client):
    app.dependency_overrides[get_provider] = lambda: AlwaysRaises()
    response = client.post("/api/complaints", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["triaged_by"] == "rules:fallback"
    assert body["category"] == "water"
    assert body["priority"] == "high"
