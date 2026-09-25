"""Minimal stand-in for the real backend.

Exists so Compose/K8s and the frontend can be built before the real API lands
(docs/PLAN.md, §2 Step 4). NOT part of the production path.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

REQUESTS = 0


class StubHandler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict, extra: dict | None = None) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        global REQUESTS
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path == "/ready":
            self._json(200, {"status": "ok", "dependencies": {"postgres": True, "redis": True}})
        elif self.path == "/api/stats":
            REQUESTS += 1
            self._json(
                200,
                {"total": 0, "by_category": {}, "by_priority": {}},
                {"X-Cache": "MISS" if REQUESTS == 1 else "HIT"},
            )
        elif self.path == "/api/meta/providers":
            self._json(200, {"active_provider": "stub", "recent_triages": []})
        elif self.path.startswith("/api/complaints"):
            self._json(200, {"items": [], "total": 0, "page": 1, "page_size": 20})
        else:
            self._json(404, {"detail": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(json.dumps({"level": "INFO", "msg": "stub", "line": fmt % args}))


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), StubHandler).serve_forever()
