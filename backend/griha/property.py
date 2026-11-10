"""Property assessment: quantile-GBM valuation with comparables, circle-rate sanity and title flags."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .models import PropertyInfo
from .synth import PIN_INDEX, PTYPES

COLS = ["tier", "pin_index", "area_sqft", "age_years", "ptype_code", "rera", "approved_plan"]


def to_frame(props: list[PropertyInfo]) -> pd.DataFrame:
    return pd.DataFrame([[p.tier, PIN_INDEX.get(p.pincode, 1.0), p.area_sqft, p.age_years, PTYPES.index(p.ptype),
                          int(p.rera_registered), int(p.approved_plan)] for p in props], columns=COLS)


class PropertyValuer:
    def __init__(self, boosters: dict, comps: pd.DataFrame):
        self.b, self.comps = boosters, comps

    def value_many(self, props: list[PropertyInfo]) -> np.ndarray:
        X = to_frame(props)
        q = np.column_stack([self.b[a].predict(X) for a in ("p10", "p50", "p90")])
        return np.sort(q, axis=1)

    def assess(self, p: PropertyInfo) -> dict:
        p10, p50, p90 = (float(x) for x in self.value_many([p])[0])
        circle_value = p.circle_rate_per_sqft * p.area_sqft
        flags = []
        if p.declared_value < circle_value:
            flags.append({"code": "BELOW_CIRCLE_RATE", "text": "Declared value is below government circle-rate value"})
        if p.declared_value > p90 * 1.10:
            flags.append({"code": "OVER_DECLARED", "text": f"Declared value is {p.declared_value / p50 - 1:.0%} above the model's median estimate"})
        if p.encumbrance:
            flags.append({"code": "ENCUMBRANCE", "text": "Existing charge/encumbrance found on title"})
        if p.litigation:
            flags.append({"code": "LITIGATION", "text": "Property is subject to litigation"})
        if not p.approved_plan:
            flags.append({"code": "UNAPPROVED_PLAN", "text": "Construction is not backed by an approved plan"})
        assessed = min(p.declared_value, p50)
        c = self.comps[(self.comps.tier == p.tier)].copy()
        c["dist"] = (np.log(c.area_sqft / p.area_sqft)).abs() + (c.pin_index - PIN_INDEX.get(p.pincode, 1.0)).abs()
        comps = c.nsmallest(5, "dist")[["area_sqft", "age_years", "value"]].round(0).to_dict("records")
        return {"p10": round(p10), "p50": round(p50), "p90": round(p90), "declared_value": p.declared_value,
                "assessed_value": round(assessed), "circle_value": round(circle_value),
                "interval_width_pct": round((p90 - p10) / p50, 3), "flags": flags, "comparables": comps,
                "title_blocked": p.litigation}
