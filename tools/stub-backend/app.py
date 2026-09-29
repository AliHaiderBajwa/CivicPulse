"""Minimal stand-in for the real backend.

Exists so Compose/K8s and the frontend can be built before the real API lands
(docs/PLAN.md, §2 Step 4). NOT part of the production path.

Implements the openapi.json contract for the paths the frontend and CI need:
POST/GET /api/complaints, GET /api/complaints/{id}, PATCH /api/complaints/{id}/status,
GET /api/stats, GET /api/meta/providers, /health, /ready — in memory only.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

STATS_REQUESTS = 0
COMPLAINTS: list[dict] = []
LOCK = threading.Lock()

# Simple fixed-window per-client rate limit (429 when exceeded), matching the
# contract's POST responses. RATE_LIMIT_PER_MIN comes from env/configmap.
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "600"))
_WINDOW: dict[str, tuple[int, int]] = {}
_WINDOW_LOCK = threading.Lock()

VALID_CATEGORIES = {"water", "electricity", "sanitation", "roads", "streetlights", "other"}
VALID_PRIORITIES = {"high", "normal", "low"}
VALID_STATUSES = {"open", "in_progress", "resolved", "rejected"}
# Stub's transition table — the real backend owns the authoritative one.
TRANSITIONS = {
    "open": {"in_progress", "rejected"},
    "in_progress": {"resolved", "rejected"},
    "resolved": {"open"},
    "rejected": {"open"},
}

CATEGORY_RULES = [
    (r"light|lamp|streetlight|dark", "streetlights"),
    (r"water|leak|pipe|sewage|drain", "water"),
    (r"garbage|trash|waste|litter|bin", "sanitation"),
    (r"pothole|road|asphalt|sidewalk|traffic", "roads"),
    (r"power|electric|outage|wire|transformer|pole", "electricity"),
]
URGENT_RULES = r"fire|gas|spark|accident|flood|downed|shock|collapse|danger|smoke"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _classify(text: str) -> tuple[str, str, str]:
    """Naive rules-based triage so the dashboard shows real variety."""
    low = text.lower()
    category = "other"
    for pattern, cat in CATEGORY_RULES:
        if re.search(pattern, low):
            category = cat
            break
    priority = "high" if re.search(URGENT_RULES, low) else ("normal" if len(low) > 60 else "low")
    summary = re.sub(r"\s+", " ", text).strip()[:137]
    return category, priority, summary


def _rate_limited(client: str) -> bool:
    now = int(time.time())
    with _WINDOW_LOCK:
        window, count = _WINDOW.get(client, (now, 0))
        if now - window >= 60:
            window, count = now, 0
        count += 1
        _WINDOW[client] = (window, count)
        return count > RATE_LIMIT_PER_MIN


class StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _client(self) -> str:
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def _json(self, code: int, body, extra: dict | None = None) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra or {}).items():
            self.send_header(k, str(v))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------ GET
    def do_GET(self) -> None:  # noqa: N802
        global STATS_REQUESTS
        url = urlparse(self.path)
        path, qs = url.path, parse_qs(url.query)

        if path == "/health":
            return self._json(200, {"status": "ok"})
        if path == "/ready":
            return self._json(200, {"status": "ok", "dependencies": {"postgres": True, "redis": True}})

        if path == "/api/stats":
            with LOCK:
                STATS_REQUESTS += 1
                by_cat: dict[str, int] = {}
                by_pri: dict[str, int] = {}
                for c in COMPLAINTS:
                    by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
                    by_pri[c["priority"]] = by_pri.get(c["priority"], 0) + 1
                return self._json(
                    200,
                    {"total": len(COMPLAINTS), "by_category": by_cat, "by_priority": by_pri},
                    {"X-Cache": "MISS" if STATS_REQUESTS == 1 else "HIT"},
                )

        if path == "/api/meta/providers":
            with LOCK:
                recent = [
                    {"provider": "rules", "latency_ms": 1, "fallback": False, "complaint_id": c["id"]}
                    for c in COMPLAINTS[-20:]
                ][::-1]
            return self._json(200, {"active_provider": "stub", "recent_triages": recent})

        if path == "/api/complaints":
            page = int(qs.get("page", ["1"])[0])
            page_size = int(qs.get("page_size", ["20"])[0])
            status = qs.get("status", [None])[0]
            category = qs.get("category", [None])[0]
            with LOCK:
                rows = list(COMPLAINTS)
            if status in VALID_STATUSES:
                rows = [c for c in rows if c["status"] == status]
            if category in VALID_CATEGORIES:
                rows = [c for c in rows if c["category"] == category]
            start = (page - 1) * page_size
            return self._json(
                200,
                {"items": rows[start : start + page_size], "total": len(rows), "page": page, "page_size": page_size},
            )

        m = re.fullmatch(r"/api/complaints/([0-9a-f-]+)", path)
        if m:
            with LOCK:
                found = next((c for c in COMPLAINTS if c["id"] == m.group(1)), None)
            if found:
                return self._json(200, found)
            return self._json(404, {"detail": "complaint not found"})

        return self._json(404, {"detail": "not found"})

    # ----------------------------------------------------------------- POST
    def do_POST(self) -> None:  # noqa: N802
        # Always consume the body FIRST: an early return with a keep-alive
        # connection would leave the body unread and the next request on that
        # connection would parse it as the request line (observed as a storm
        # of 400s during the k6 load test).
        body = self._read_body()
        url = urlparse(self.path)
        if url.path != "/api/complaints":
            return self._json(404, {"detail": "not found"})
        if _rate_limited(self._client()):
            return self._json(429, {"detail": "rate limit exceeded, slow down"})

        if body is None:
            return self._json(400, {"detail": "request body must be a JSON object"})

        text = body.get("text")
        location = body.get("location")
        contact = body.get("reporter_contact")
        if not isinstance(text, str) or not 10 <= len(text) <= 2000:
            return self._json(400, {"detail": "text must be between 10 and 2000 characters"})
        if not isinstance(location, str) or not 3 <= len(location) <= 200:
            return self._json(400, {"detail": "location must be between 3 and 200 characters"})
        if contact is not None and (not isinstance(contact, str) or len(contact) > 200):
            return self._json(400, {"detail": "reporter_contact must be at most 200 characters"})

        category, priority, summary = _classify(text)
        now = _now()
        complaint = {
            "id": str(uuid.uuid4()),
            "text": text,
            "location": location,
            "reporter_contact": contact,
            "category": category,
            "priority": priority,
            "status": "open",
            "ai_summary": summary,
            "triaged_by": "rules",
            "triage_latency_ms": 1,
            "created_at": now,
            "updated_at": now,
        }
        with LOCK:
            COMPLAINTS.append(complaint)
        return self._json(201, complaint, {"Location": f"/api/complaints/{complaint['id']}"})

    # ---------------------------------------------------------------- PATCH
    def do_PATCH(self) -> None:  # noqa: N802
        body = self._read_body()  # drain before any early return (keep-alive)
        m = re.fullmatch(r"/api/complaints/([0-9a-f-]+)/status", urlparse(self.path).path)
        if not m:
            return self._json(404, {"detail": "not found"})
        if _rate_limited(self._client()):
            return self._json(429, {"detail": "rate limit exceeded, slow down"})

        if body is None:
            return self._json(400, {"detail": "request body must be a JSON object"})
        new_status = body.get("status")
        if new_status not in VALID_STATUSES:
            return self._json(400, {"detail": f"status must be one of {sorted(VALID_STATUSES)}"})

        with LOCK:
            found = next((c for c in COMPLAINTS if c["id"] == m.group(1)), None)
            if not found:
                return self._json(404, {"detail": "complaint not found"})
            if new_status not in TRANSITIONS[found["status"]]:
                return self._json(
                    409,
                    {"detail": f"cannot transition from '{found['status']}' to '{new_status}'"},
                )
            found["status"] = new_status
            found["updated_at"] = _now()
            snapshot = dict(found)
        return self._json(200, snapshot)

    def log_message(self, fmt: str, *args) -> None:
        print(json.dumps({"level": "INFO", "msg": "stub", "line": fmt % args}))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), StubHandler).serve_forever()
