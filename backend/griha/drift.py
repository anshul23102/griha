"""Model drift monitoring: Population Stability Index (PSI) of live risk inputs against a reference population.

Reference = the same synthetic population family the model was trained on (cases 50000+, disjoint from training seeds 1000+),
scored by this engine. Live = the risk-stage features of cases served since start. PSI per feature over reference deciles;
conventional reading: < 0.10 stable, 0.10 to 0.25 shifted, > 0.25 drifted. Prepared demo scenarios are not a random sample of
applicants, so some drift is expected in a demo; the machinery is what a lender would point at real traffic."""
from __future__ import annotations

import math

import numpy as np

from .features import FEATURES

MIN_LIVE = 100          # PSI over 10 bins is noisy below ~100 cases (expected noise ~ 9 x (1/live + 1/reference))
CONTINUOUS = ["foir", "ltv", "bureau_score", "income_cv", "buffer_months", "enquiries_6m", "age", "tenure_years", "loan_to_income"]


def risk_features(decision) -> dict | None:
    for e in decision.evidence:
        if e.stage == "risk" and isinstance(e.data, dict) and e.data.get("features"):
            return e.data["features"]
    return None


def build_reference(engine, n: int = 500) -> dict[str, list[float]]:
    from .synth import make_case
    cols: dict[str, list[float]] = {f: [] for f in CONTINUOUS}
    for i in range(n):
        app, _ = make_case(50000 + i)
        f = risk_features(engine.underwrite(app, record=False))
        if f:
            for k in CONTINUOUS:
                if f.get(k) is not None:
                    cols[k].append(float(f[k]))
    return cols


def psi(reference: list[float], live: list[float], bins: int = 10) -> float:
    ref = np.asarray(reference, float)
    liv = np.asarray(live, float)
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)[1:-1]))
    e = np.bincount(np.searchsorted(edges, ref, side="right"), minlength=len(edges) + 1) / len(ref)
    a = np.bincount(np.searchsorted(edges, liv, side="right"), minlength=len(edges) + 1) / len(liv)
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def status(v: float) -> str:
    return "stable" if v < 0.10 else "shifted" if v < 0.25 else "drifted"


def report(reference: dict[str, list[float]] | None, decisions) -> dict:
    if not reference:
        return {"state": "warming", "min_live": MIN_LIVE, "live": 0, "features": []}
    live: dict[str, list[float]] = {f: [] for f in CONTINUOUS}
    n = 0
    for d in decisions:
        f = risk_features(d)
        if f:
            n += 1
            for k in CONTINUOUS:
                if f.get(k) is not None:
                    live[k].append(float(f[k]))
    if n < MIN_LIVE:
        return {"state": "collecting", "min_live": MIN_LIVE, "live": n, "reference": len(next(iter(reference.values()))), "features": []}
    rows = []
    for k in CONTINUOUS:
        if len(live[k]) >= MIN_LIVE and reference.get(k):
            v = psi(reference[k], live[k])
            rows.append({"feature": k, "psi": round(v, 3), "status": status(v), "ref_median": round(float(np.median(reference[k])), 3),
                         "live_median": round(float(np.median(live[k])), 3)})
    worst = max((r["psi"] for r in rows), default=0.0)
    return {"state": "ready", "min_live": MIN_LIVE, "live": n, "reference": len(next(iter(reference.values()))), "features": rows,
            "overall": status(worst), "worst": round(worst, 3)}
