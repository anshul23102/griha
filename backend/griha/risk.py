"""Probability-of-default model: monotone-constrained LightGBM bagged ensemble, isotonic calibration,
Mondrian conformal prediction sets, and native SHAP contributions for reason codes."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .features import FEATURES, LABELS


def _fmt(feat: str, v: float) -> str:
    if feat in ("foir", "ltv", "loan_to_income", "income_cv"):
        return f"{v:.0%}" if feat != "loan_to_income" else f"{v:.1f}x"
    if feat == "buffer_months":
        return f"{v:.1f} EMIs"
    if feat == "tenure_years" or feat == "age":
        return f"{v:.0f} yrs"
    if feat == "self_employed":
        return "yes" if v else "no"
    return "n/a (thin file)" if (isinstance(v, float) and math.isnan(v)) else f"{v:.0f}"


def score_from_pd(p: float) -> int:
    """Scorecard scaling: 650 points at 30:1 good:bad odds, 40 points to double the odds."""
    odds = (1 - p) / max(p, 1e-4)
    return int(round(max(300, min(900, 650 + (40 / math.log(2)) * math.log(odds / 30)))))


def band_of(score: int) -> str:
    return "A" if score >= 700 else "B" if score >= 640 else "C" if score >= 590 else "D" if score >= 540 else "E"


class RiskModel:
    def __init__(self, boosters, iso, qhat, version):
        self.boosters, self.iso, self.qhat, self.version = boosters, iso, qhat, version

    def _frame(self, feats: dict) -> pd.DataFrame:
        return pd.DataFrame([[feats[f] for f in FEATURES]], columns=FEATURES)

    def predict_many(self, X: pd.DataFrame) -> np.ndarray:
        raw = np.column_stack([b.predict(X[FEATURES]) for b in self.boosters])
        return self.iso.predict(raw.ravel()).reshape(raw.shape)

    def conformal_set(self, p: float) -> list[int]:
        s = []
        if 1 - (1 - p) <= self.qhat[0]:      # label 0 (repays): nonconformity = 1-p(0) = p
            s.append(0)
        if 1 - p <= self.qhat[1]:            # label 1 (defaults)
            s.append(1)
        return s

    def predict(self, feats: dict) -> dict:
        X = self._frame(feats)
        cal = self.predict_many(X)[0]
        p = float(np.mean(cal))
        lo, hi = float(np.percentile(cal, 10)), float(np.percentile(cal, 90))
        contrib = np.mean([b.predict(X, pred_contrib=True)[0] for b in self.boosters], axis=0)
        phi = dict(zip(FEATURES, contrib[:-1]))
        order = sorted(phi, key=lambda k: -abs(phi[k]))
        drivers = [{"feature": k, "label": LABELS[k], "value": _fmt(k, feats[k]), "log_odds": round(float(phi[k]), 3),
                    "direction": "adverse" if phi[k] > 0 else "favourable"} for k in order[:6]]
        cs = self.conformal_set(p)
        sc = score_from_pd(p)
        return {"score": sc, "band": band_of(sc), "pd": round(p, 4), "pd_lo": round(lo, 4), "pd_hi": round(hi, 4), "conformal_set": cs,
                "certain": len(cs) == 1, "drivers": drivers}
