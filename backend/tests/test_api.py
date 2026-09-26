import uuid

from tests.conftest import VALID

WATER = {"text": "water main burst flooding the street outside", "location": "Street 12"}
ELEC = {"text": "load shedding every evening in our area", "location": "Gulberg"}
SANI = {"text": "garbage not collected for weeks now", "location": "Block C"}


def test_create_persists_and_returns_201(client):
    r = client.post("/api/complaints", json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["triaged_by"] == "simulated"
    fetched = client.get(f"/api/complaints/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["text"] == VALID["text"]


def test_get_unknown_id_is_404(client):
    r = client.get(f"/api/complaints/{uuid.uuid4()}")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"]


def test_validation_errors_are_400_and_field_level(client):
    r = client.post("/api/complaints", json={"text": "too short", "location": "Street 12"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail[0]["field"] == "text"
    assert detail[0]["message"]


def test_malformed_json_body_is_400(client):
    r = client.post(
        "/api/complaints", content="{not json", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400
    assert isinstance(r.json()["detail"], list)


def test_page_size_over_100_is_400(client):
    r = client.get("/api/complaints", params={"page_size": 101})
    assert r.status_code == 400
    assert r.json()["detail"][0]["field"] == "page_size"


def test_list_filters_and_pagination(client):
    for payload in (WATER, ELEC, SANI):
        assert client.post("/api/complaints", json=payload).status_code == 201

    filtered = client.get("/api/complaints", params={"category": "electricity"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert all(item["category"] == "electricity" for item in filtered.json()["items"])

    paged = client.get("/api/complaints", params={"page": 1, "page_size": 2})
    assert len(paged.json()["items"]) == 2
    assert paged.json()["total"] == 3

    second_page = client.get("/api/complaints", params={"page": 2, "page_size": 2})
    assert len(second_page.json()["items"]) == 1


def test_invalid_transition_is_409_naming_it(client):
    body = client.post("/api/complaints", json=VALID).json()
    r = client.patch(f"/api/complaints/{body['id']}/status", json={"status": "resolved"})
    assert r.status_code == 409
    assert "open -> resolved" in r.json()["detail"]


def test_valid_transition_chain(client):
    body = client.post("/api/complaints", json=VALID).json()
    cid = body["id"]
    in_progress = client.patch(f"/api/complaints/{cid}/status", json={"status": "in_progress"})
    assert in_progress.status_code == 200
    assert in_progress.json()["status"] == "in_progress"
    resolved = client.patch(f"/api/complaints/{cid}/status", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    reopen = client.patch(f"/api/complaints/{cid}/status", json={"status": "open"})
    assert reopen.status_code == 409
    assert "resolved -> open" in reopen.json()["detail"]


def test_request_id_is_echoed_and_generated(client):
    sent = client.get("/health", headers={"X-Request-ID": "abc"})
    assert sent.headers["x-request-id"] == "abc"
    generated = client.get("/health")
    assert generated.headers["x-request-id"]
    assert generated.headers["x-request-id"] != "abc"
