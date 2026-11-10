"""Closed-loop load test of the real API: each virtual user posts a prepared synthetic application and waits for the decision.
Reports throughput and latency percentiles per concurrency level. Point it at a dedicated instance with a high rate limit:

    GRIHA_API_LIMIT=1000000 GRIHA_ORCHESTRATOR=inline GRIHA_DATA_DIR=/tmp/lt uv run uvicorn griha.api:app --port 8001 [--workers N]
    uv run python -m tools.loadtest --url http://127.0.0.1:8001 --levels 1,2,4,8 --seconds 15
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import httpx

SCENARIOS = ["salaried_approve", "refer_gap", "salaried_approve", "salaried_approve"]       # mostly approvals, some referrals


async def user(client: httpx.AsyncClient, stop: float, out: list, errs: list) -> None:
    i = 0
    while time.perf_counter() < stop:
        t0 = time.perf_counter()
        try:
            r = await client.post("/api/applications", json={"scenario_id": SCENARIOS[i % len(SCENARIOS)]})
            ok = r.status_code == 200
        except httpx.HTTPError as e:
            ok, r = False, None
            errs.append(type(e).__name__)
        dt = (time.perf_counter() - t0) * 1000
        if ok:
            out.append(dt)
        elif r is not None:
            errs.append(str(r.status_code))
        i += 1


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))], 1)


async def level(url: str, users: int, seconds: float) -> dict:
    out: list[float] = []
    errs: list[str] = []
    limits = httpx.Limits(max_connections=users + 2)
    async with httpx.AsyncClient(base_url=url, timeout=60, limits=limits) as c:
        await c.get("/api/health")
        t0 = time.perf_counter()
        stop = t0 + seconds
        await asyncio.gather(*[user(c, stop, out, errs) for _ in range(users)])
        wall = time.perf_counter() - t0
    return {"users": users, "decisions": len(out), "per_second": round(len(out) / wall, 1), "p50_ms": pct(out, 0.5) if out else None,
            "p95_ms": pct(out, 0.95) if out else None, "p99_ms": pct(out, 0.99) if out else None, "mean_ms": round(statistics.mean(out), 1) if out else None,
            "errors": len(errs), "error_kinds": sorted(set(errs))}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8001")
    ap.add_argument("--levels", default="1,2,4,8")
    ap.add_argument("--seconds", type=float, default=15)
    a = ap.parse_args()
    rows = []
    print(f"{'users':>5} {'decisions':>9} {'per s':>7} {'p50 ms':>8} {'p95 ms':>8} {'p99 ms':>8} {'errors':>7}")
    for n in [int(x) for x in a.levels.split(",")]:
        r = await level(a.url, n, a.seconds)
        rows.append(r)
        print(f"{r['users']:>5} {r['decisions']:>9} {r['per_second']:>7} {r['p50_ms']:>8} {r['p95_ms']:>8} {r['p99_ms']:>8} {r['errors']:>7}")
    print(json.dumps(rows))


if __name__ == "__main__":
    asyncio.run(main())
