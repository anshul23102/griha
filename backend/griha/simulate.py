"""Policy Impact Simulator: replay a stored synthetic portfolio under a changed policy before shipping it."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from .models import Decision
from .synth import make_case

NO_GRAPH = {"shared_phone_other_pan": False, "shared_property_other_applicant": False, "ring_size": 1}


def fair_row(name: str, groups: dict) -> dict | None:
    """Approval-rate ratio (lowest group / highest group) within ONE attribute, with a 95% interval, so a small-sample wobble is not read as bias.
    flag = 'below_80_significant' only when the whole interval sits under 0.80 (four-fifths rule used as a screen, not as a legal test)."""
    g = {k: v for k, v in groups.items() if v[0] >= 20}
    if len(g) < 2:
        return None
    rate = {k: v[1] / v[0] for k, v in g.items()}
    lo_k, hi_k = min(rate, key=rate.get), max(rate, key=rate.get)
    if rate[hi_k] == 0 or rate[lo_k] == 0:
        return None
    (n1, a1), (n2, a2) = g[lo_k], g[hi_k]
    ratio = rate[lo_k] / rate[hi_k]
    se = math.sqrt((1 - rate[lo_k]) / max(a1, 1) + (1 - rate[hi_k]) / max(a2, 1))   # standard error of ln(ratio)
    lo, hi = ratio * math.exp(-1.96 * se), ratio * math.exp(1.96 * se)
    flag = "ok" if ratio >= 0.8 else ("below_80_significant" if hi < 0.8 else "below_80_not_significant")
    return {"attribute": name, "lowest": str(lo_k), "highest": str(hi_k), "ratio": round(ratio, 3), "ci95": [round(lo, 3), round(min(hi, 9.99), 3)],
            "n": [n1, n2], "flag": flag}


class Portfolio:
    def __init__(self, n: int = 400, seed0: int = 300_000):
        self.items = []
        for i in range(n):
            fraud = ["edit", "dressing"][i % 2] if i % 20 == 0 else None
            app, truth = make_case(seed0 + i, fraud=fraud)
            self.items.append((app, truth))

    def run(self, engine, policy) -> dict:
        outcomes = defaultdict(int)
        vol = el = 0.0
        defaults = approved = 0
        by_gender: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        by_tier: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        per_case = []
        ms = []
        for app, truth in self.items:
            d: Decision = engine.underwrite(app, policy=policy, graph_flags=NO_GRAPH, record=False)
            outcomes[d.outcome] += 1
            ms.append(sum(e.ms for e in d.evidence))
            ok = d.outcome == "APPROVE"
            per_case.append((app.case_id, d.outcome))
            for grp, key in ((by_gender, app.applicant.gender), (by_tier, app.applicant.city_tier)):
                grp[key][0] += 1
                grp[key][1] += ok
            if ok:
                approved += 1
                amt = d.offer["amount"]
                vol += amt
                el += amt * d.pd["pd"]
                defaults += truth["default"]
        n = len(self.items)
        fairness = [fair_row("gender", by_gender), fair_row("tier", by_tier)]
        fairness = [x for x in fairness if x]
        rates = {f"gender_{k}": v[1] / v[0] for k, v in by_gender.items() if v[0] >= 20}
        rates |= {f"tier_{k}": v[1] / v[0] for k, v in by_tier.items() if v[0] >= 20}
        worst = min(fairness, key=lambda x: x["ratio"]) if fairness else None
        air = worst["ratio"] if worst else None
        return {"n": n, "approve_rate": outcomes["APPROVE"] / n, "refer_rate": outcomes["REFER"] / n, "reject_rate": outcomes["REJECT"] / n,
                "approved_volume": vol, "expected_loss_pct": (el / vol) if vol else 0.0,
                "realised_default_rate_approved": (defaults / approved) if approved else 0.0,
                "approval_rate_by_group": {k: round(v, 3) for k, v in rates.items()}, "adverse_impact_ratio": round(air, 3) if air else None, "fairness": fairness,
                "engine_ms_median": round(statistics.median(ms), 2), "engine_ms_p95": round(sorted(ms)[int(len(ms) * 0.95) - 1], 2),
                "_cases": per_case}

    def compare(self, engine, changes: dict, base: dict | None = None) -> dict:
        base = base or self.run(engine, engine.policy)
        base = {**base, "_cases": list(base["_cases"])}
        new = self.run(engine, engine.policy.with_changes(changes))
        flipped = [{"case_id": c, "from": o1, "to": o2} for (c, o1), (_, o2) in zip(base.pop("_cases"), new.pop("_cases")) if o1 != o2]
        return {"changes": changes, "baseline": base, "scenario": new, "flipped": len(flipped), "flipped_examples": flipped[:8]}
