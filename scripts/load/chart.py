#!/usr/bin/env python3
"""Replicas-vs-load chart from the real k6 run + HPA sampling (rubric H5).

Inputs (committed evidence):
  docs/evidence/16-hpa-collect.csv   timestamp,replicas,cpu_percent (5s samples)
  docs/evidence/17-k6-rps.csv        timestamp,rps (5s buckets from k6 JSON out)
Output:
  docs/evidence/18-hpa-load-chart.png
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

EVID = Path(__file__).resolve().parents[2] / "docs" / "evidence"


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def load_hpa() -> list[tuple[datetime, int, int | None]]:
    rows = []
    with open(EVID / "16-hpa-collect.csv") as f:
        for r in csv.DictReader(f):
            if not r["timestamp"] or r["timestamp"] == "timestamp":
                continue
            rows.append(
                (parse(r["timestamp"]), int(r["replicas"]), int(r["cpu_percent"]) if r["cpu_percent"] else None)
            )
    return rows


def load_rps() -> list[tuple[datetime, float]]:
    rows = []
    with open(EVID / "17-k6-rps.csv") as f:
        for r in csv.DictReader(f):
            rows.append((parse(r["timestamp"]), float(r["rps"])))
    return rows


def main() -> None:
    hpa = load_hpa()
    rps = load_rps()
    x_h = [r[0] for r in hpa]
    replicas = [r[1] for r in hpa]
    cpu = [r[2] for r in hpa]
    x_r = [r[0] for r in rps]
    rate = [r[1] for r in rps]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 2]}
    )

    if rps:
        ax1.fill_between(x_r, rate, step="post", alpha=0.3, color="tab:blue", label="request rate (req/s)")
        ax1.plot(x_r, rate, ds="steps-post", color="tab:blue", lw=1)
        ax1.set_ylabel("requests / second", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")
        ax1.axvspan(x_r[0], x_r[-1], color="tab:blue", alpha=0.06)

    ax1b = ax1.twinx()
    ax1b.step(x_h, replicas, where="post", color="tab:red", lw=2, label="backend replicas")
    ax1b.set_ylabel("backend replicas", color="tab:red")
    ax1b.tick_params(axis="y", labelcolor="tab:red")
    ax1b.set_ylim(0, max(replicas) + 2)
    ax1.set_title("CivicPulse HPA under real k6 load — replicas vs request rate")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax2.plot(x_h, cpu, color="tab:green", lw=1.5, label="CPU utilisation (avg % of request)")
    ax2.axhline(60, color="tab:red", ls="--", lw=1, label="HPA target 60%")
    ax2.set_ylabel("CPU %")
    ax2.set_ylim(bottom=0)
    ax2.legend(loc="upper right")
    ax2.set_xlabel("time")

    fig.autofmt_xdate()
    fig.tight_layout()
    out = EVID / "18-hpa-load-chart.png"
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
