#!/usr/bin/env python3
"""Measure the triage content-hash cache hit rate (rubric F4).

Posts ``REPEATS`` copies of each of ``UNIQUES`` distinct complaint texts to
``POST /api/complaints``, then reads the ``triage_cache_total`` counter deltas
from ``GET /metrics``. The expected rate for a perfectly hash-keyed cache is
``(REPEATS - 1) / REPEATS``: the first copy of each text misses, every repeat
hits.

Only the standard library is used, so this runs with any Python >= 3.10 against
a running stack (compose, k8s port-forward, or ``uvicorn app.main:app``):

    BASE_URL=http://127.0.0.1:8000 python scripts/triage_hit_rate.py

Each request carries a rotating ``X-Forwarded-For`` so the 10/min per-client
POST limiter sees 10x1 clients instead of one client with 40 requests - the
cache measurement must not be polluted by 429s.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

COUNTER_RE = re.compile(r"^triage_cache_total\{result=\"(?P<result>[^\"]+)\"\}\s+(?P<value>[\d.]+)", re.M)
FALLBACK_RE = re.compile(r"^triage_fallback_total\{[^}]*\}\s+(?P<value>[\d.]+)", re.M)


def fetch(url: str, payload: bytes | None = None, headers: dict | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, data=payload, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:  # 4xx/5xx still carry the body we want
        return exc.code, exc.read().decode()


def cache_counters(metrics_text: str) -> dict[str, float]:
    found = {m.group("result"): float(m.group("value")) for m in COUNTER_RE.finditer(metrics_text)}
    return {"hit": found.get("hit", 0.0), "miss": found.get("miss", 0.0)}


def fallback_total(metrics_text: str) -> float:
    return sum(float(m.group("value")) for m in FALLBACK_RE.finditer(metrics_text))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--uniques", type=int, default=10, help="distinct complaint texts")
    ap.add_argument("--repeats", type=int, default=4, help="POSTs per distinct text")
    ap.add_argument("--nonce", default=None, help="probe id; default is time-derived (cold cache)")
    args = ap.parse_args()

    nonce = args.nonce or hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]
    base = args.base_url.rstrip("/")

    status, metrics_before = fetch(f"{base}/metrics")
    if status != 200:
        print(f"GET /metrics -> {status}", file=sys.stderr)
        return 1
    before = cache_counters(metrics_before)
    fallback_before = fallback_total(metrics_before)

    statuses: list[int] = []
    for i in range(args.uniques):
        text = f"Duplicate-submit cache probe {i} ({nonce}): streetlight out near Block {i}"
        body = json.dumps({"text": text, "location": "Probe Street"}).encode()
        for r in range(args.repeats):
            # Rotate the client identity: the per-POST limiter is 10/min/client.
            client = f"10.9.8.{(i * args.repeats + r) % 250 + 1}"
            status, _ = fetch(
                f"{base}/api/complaints",
                payload=body,
                headers={"Content-Type": "application/json", "X-Forwarded-For": client},
            )
            statuses.append(status)

    status, metrics_after = fetch(f"{base}/metrics")
    after = cache_counters(metrics_after)
    hits = after["hit"] - before["hit"]
    misses = after["miss"] - before["miss"]
    fallbacks = fallback_total(metrics_after) - fallback_before
    lookups = hits + misses
    hit_rate = hits / lookups if lookups else 0.0
    expected = (args.repeats - 1) / args.repeats

    report = {
        "base_url": base,
        "nonce": nonce,
        "posts": len(statuses),
        "post_statuses": sorted(set(statuses)),
        "uniques": args.uniques,
        "repeats": args.repeats,
        "cache_hits": int(hits),
        "cache_misses": int(misses),
        "cache_lookups": int(lookups),
        "hit_rate": round(hit_rate, 4),
        "expected_hit_rate": round(expected, 4),
        "fallbacks_during_run": int(fallbacks),
        "all_201": statuses == [201] * len(statuses),
    }
    print(json.dumps(report, indent=2))

    ok = (
        report["all_201"]
        and hits == args.uniques * (args.repeats - 1)
        and misses == args.uniques
        and fallbacks == 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
