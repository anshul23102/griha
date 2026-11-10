"""Out-of-generator validation of Griha's modelling recipe on two PUBLIC, REAL credit datasets that carry an open licence.

Why: every metric the shipped model reports is measured on data our own generator makes. This tool runs the same recipe (monotone-constrained
LightGBM + isotonic calibration, against a plain logistic baseline) on real borrowers' outcomes the generator does not control.

Datasets (both UCI Machine Learning Repository, licence CC BY 4.0, free to use and share with attribution):
  * Statlog (German Credit Data), Hofmann H., 1994, doi:10.24432/C5NC77. 1,000 loans from a German bank, 30% bad.
  * Default of Credit Card Clients, Yeh I-C., 2009, doi:10.24432/C55S3H. 30,000 Taiwanese card holders, 22% default next month.

What this is NOT: Indian calibration, or mortgage data. German Credit is instalment credit, Taiwan is cards. The point is narrower: on real
outcomes, does monotone-constrained boosting keep its ranking power versus an unconstrained model and a logistic baseline, and are the
isotonic probabilities calibrated out of sample? Monotone directions are set only on features whose direction is not in doubt.

Data stay in data-external/uci (not committed). Run from backend/:   uv run python -m tools.validate_public
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", message=".*xlrd engine.*")
ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data-external" / "uci"
OUT = ROOT / "backend" / "artifacts" / "real_data_validation.json"

GERMAN_COLS = ["status", "duration", "history", "purpose", "amount", "savings", "employment", "installment_rate", "personal", "debtors",
               "residence", "property", "age", "other_plans", "housing", "existing_credits", "job", "dependents", "telephone", "foreign", "bad"]
# direction known with confidence: longer term, bigger amount and a higher instalment-to-income rate never lower default risk
GERMAN_MONO = {"duration": 1, "amount": 1, "installment_rate": 1}
TAIWAN_MONO = {**{f"PAY_{i}": 1 for i in (0, 2, 3, 4, 5, 6)}, "LIMIT_BAL": -1}   # more months late -> riskier; higher limit -> safer


def load_german() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(DATA / "german" / "german.data", sep=r"\s+", header=None, names=GERMAN_COLS)
    y = (df.pop("bad") == 2).astype(int).to_numpy()
    return pd.get_dummies(df, dtype=float), y


def load_taiwan() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_excel(next((DATA / "taiwan").glob("*.xls")), header=1).drop(columns=["ID"])
    y = df.pop("default payment next month").astype(int).to_numpy()
    return df.astype(float), y


def ks(y, p) -> float:
    o = np.argsort(p)
    ys = y[o]
    return float(np.max(np.abs(np.cumsum(ys == 0) / max((ys == 0).sum(), 1) - np.cumsum(ys == 1) / max((ys == 1).sum(), 1))))


def gbm(mono: list[int], n: int):
    return lgb.LGBMClassifier(n_estimators=250 if n > 5000 else 150, learning_rate=0.04, num_leaves=8, min_child_samples=max(20, n // 200),
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, monotone_constraints=mono or None, verbose=-1, random_state=7)


def evaluate(name: str, X: pd.DataFrame, y: np.ndarray, mono_map: dict[str, int], repeats: int = 3) -> dict:
    mono = [mono_map.get(c, 0) for c in X.columns]
    res: dict[str, list] = {k: [] for k in ("logit", "gbm_free", "gbm_monotone")}
    cal = {"pred": [], "obs": []}
    for rep in range(repeats):
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=rep).split(X, y):
            Xtr, Xte, ytr, yte = X.iloc[tr], X.iloc[te], y[tr], y[te]
            models = {
                "logit": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5)),
                "gbm_free": CalibratedClassifierCV(gbm([], len(X)), method="isotonic", cv=3),
                "gbm_monotone": CalibratedClassifierCV(gbm(mono, len(X)), method="isotonic", cv=3),
            }
            for k, m in models.items():
                m.fit(Xtr, ytr)
                p = m.predict_proba(Xte)[:, 1]
                res[k].append((roc_auc_score(yte, p), ks(yte, p), brier_score_loss(yte, p)))
                if k == "gbm_monotone":
                    cal["pred"].extend(p)
                    cal["obs"].extend(yte)
    out = {"dataset": name, "n": int(len(y)), "bad_rate": round(float(y.mean()), 4), "folds": 5 * repeats, "monotone_features": sorted(mono_map)}
    for k, v in res.items():
        a = np.array(v)
        out[k] = {"auc": round(float(a[:, 0].mean()), 4), "auc_sd": round(float(a[:, 0].std()), 4), "ks": round(float(a[:, 1].mean()), 4),
                  "brier": round(float(a[:, 2].mean()), 4)}
    p, o = np.array(cal["pred"]), np.array(cal["obs"])
    dec = np.digitize(p, np.quantile(p, np.linspace(0.1, 0.9, 9)))
    out["calibration_deciles"] = [{"decile": int(d) + 1, "mean_pred": round(float(p[dec == d].mean()), 4), "observed": round(float(o[dec == d].mean()), 4)}
                                  for d in range(10) if (dec == d).any()]
    out["calibration_gap_mean_abs"] = round(float(np.mean([abs(r["mean_pred"] - r["observed"]) for r in out["calibration_deciles"]])), 4)
    return out


def main() -> None:
    results = [evaluate("German Credit (UCI, CC BY 4.0)", *load_german(), GERMAN_MONO),
               evaluate("Taiwan credit-card default (UCI, CC BY 4.0)", *load_taiwan(), TAIWAN_MONO, repeats=1)]
    OUT.write_text(json.dumps({"note": "Out-of-sample, 5-fold stratified cross-validation. Real outcomes, not Indian mortgages. Data: UCI Machine Learning Repository, CC BY 4.0.", "sources": ["https://doi.org/10.24432/C5NC77", "https://doi.org/10.24432/C55S3H"], "results": results}, indent=1))
    for r in results:
        print(f"\n{r['dataset']}  n={r['n']}  bad={r['bad_rate']:.1%}")
        for k in ("logit", "gbm_free", "gbm_monotone"):
            print(f"  {k:13s} AUC {r[k]['auc']:.3f} (sd {r[k]['auc_sd']:.3f})  KS {r[k]['ks']:.3f}  Brier {r[k]['brier']:.4f}")
        print(f"  mean |pred-observed| per decile: {r['calibration_gap_mean_abs']:.4f}")


if __name__ == "__main__":
    main()
