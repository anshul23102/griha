"""Train every learned component on the synthetic world and write artifacts. Run: python -m griha.train"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from . import config, features, fraud, income
from .features import FEATURES, MONOTONE
from .property import COLS, PropertyValuer, to_frame
from .risk import RiskModel
from .synth import make_case

N_HONEST, N_FRAUD = 5200, 0

log = logging.getLogger("griha.train")


def main(n: int = N_HONEST):
    t0 = time.time()
    config.ARTIFACTS.mkdir(exist_ok=True)
    cases = [make_case(1000 + i) for i in range(n)]
    log.info(f"generated {n} cases in {time.time() - t0:.0f}s")

    # ---- property valuation (quantile GBMs) ----
    props = [a.property for a, _ in cases]
    Xp = to_frame(props)
    yp = np.array([t["market_value"] for _, t in cases])
    cut = int(0.8 * n)
    boosters = {}
    for name, alpha in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9)):
        boosters[name] = lgb.train({"objective": "quantile", "alpha": alpha, "learning_rate": 0.05, "num_leaves": 15,
                                    "min_data_in_leaf": 30, "verbose": -1, "seed": 1},
                                   lgb.Dataset(Xp[:cut], yp[:cut]), 300)
    comps = Xp.copy()
    comps["value"] = yp
    valuer = PropertyValuer(boosters, comps.iloc[:cut].reset_index(drop=True))
    q = valuer.value_many(props[cut:])
    pp = q[:, 1]
    prop_metrics = {"ppe10": float(np.mean(np.abs(pp / yp[cut:] - 1) <= 0.10)),
                    "mape": float(np.mean(np.abs(pp / yp[cut:] - 1))),
                    "interval_coverage_80": float(np.mean((yp[cut:] >= q[:, 0]) & (yp[cut:] <= q[:, 2])))}
    log.info("property %s", prop_metrics)

    # ---- risk features on honest population ----
    rows, ys, assessed_all = [], [], valuer.value_many(props)[:, 1]
    incs = []
    for (a, t), av in zip(cases, assessed_all):
        inc = income.analyse(a.statement, a.applicant.employment, a.applicant.declared_monthly_income,
                             a.bureau.active_obligations_monthly if a.bureau else None)
        incs.append(inc)
        assessed = min(a.property.declared_value, float(av))
        rows.append(features.build(a, inc, assessed, a.loan.amount, a.loan.tenure_months))
        ys.append(t["default"])
    X, y = pd.DataFrame(rows)[FEATURES], np.array(ys)
    log.info(f"features built; default rate {y.mean():.3f}")

    n_tr, n_va, n_cal = int(0.62 * n), int(0.14 * n), int(0.12 * n)
    sl = {"tr": slice(0, n_tr), "va": slice(n_tr, n_tr + n_va), "cal": slice(n_tr + n_va, n_tr + n_va + n_cal),
          "te": slice(n_tr + n_va + n_cal, n)}
    models, rng = [], np.random.default_rng(5)
    for k in range(5):
        idx = rng.choice(n_tr, size=n_tr, replace=True)
        params = {"objective": "binary", "learning_rate": 0.03, "num_leaves": 4, "min_data_in_leaf": 80, "lambda_l2": 10.0,
                  "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 1, "monotone_constraints": MONOTONE,
                  "monotone_constraints_method": "advanced", "verbose": -1, "seed": 100 + k}
        dtr = lgb.Dataset(X.iloc[idx], y[idx])
        dva = lgb.Dataset(X.iloc[sl["va"]], y[sl["va"]])
        models.append(lgb.train(params, dtr, 600, valid_sets=[dva], callbacks=[lgb.early_stopping(40, verbose=False)]))
    raw_cal = np.mean([m.predict(X.iloc[sl["cal"]]) for m in models], axis=0)
    # isotonic on ensemble-mean raw prediction; applied per-member at inference (members are similar in scale)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0005, y_max=0.95).fit(raw_cal, y[sl["cal"]])
    p_cal = iso.predict(raw_cal)
    # Mondrian conformal, alpha=0.1
    alpha, qhat = 0.1, []
    for lab in (0, 1):
        s = np.sort((p_cal if lab == 0 else 1 - p_cal)[y[sl["cal"]] == lab])
        k = min(len(s) - 1, int(np.ceil((len(s) + 1) * (1 - alpha))) - 1)
        qhat.append(float(s[k]))
    version = hashlib.sha256(json.dumps([str(m.model_to_string())[:2000] for m in models]).encode()).hexdigest()[:12]
    risk = RiskModel(models, iso, qhat, version)

    pte = risk.predict_many(X.iloc[sl["te"]]).mean(axis=1)
    yte = y[sl["te"]]
    order = np.argsort(-pte)
    ks = float(np.max(np.abs(np.cumsum(yte[order] == 1) / max(yte.sum(), 1) - np.cumsum(yte[order] == 0) / max((1 - yte).sum(), 1))))
    cov = {lab: float(np.mean([(lab in risk.conformal_set(p)) for p, yy in zip(pte, yte) if yy == lab])) for lab in (0, 1)}
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    Xte = X.iloc[sl["te"]]
    lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500)).fit(X.iloc[sl["tr"]], y[sl["tr"]])
    bur = Xte["bureau_score"].fillna(X["bureau_score"].median())
    baselines = {"foir_only": float(roc_auc_score(yte, Xte["foir"])), "bureau_only": float(roc_auc_score(yte, -bur)),
                 "logistic": float(roc_auc_score(yte, lr.predict_proba(Xte)[:, 1])), "griha_gbm": float(roc_auc_score(yte, pte))}
    order_b = np.argsort(pte)
    calibration = [{"bin": i + 1, "n": int(len(ix)), "predicted": float(pte[ix].mean()), "actual": float(yte[ix].mean())}
                   for i, ix in enumerate(np.array_split(order_b, 10))]
    risk_metrics = {"baselines": baselines, "calibration": calibration, "auc": float(roc_auc_score(yte, pte)), "ks": ks, "brier": float(brier_score_loss(yte, pte)),
                    "base_rate_train": float(y.mean()), "mean_pred_test": float(pte.mean()), "actual_test": float(yte.mean()),
                    "conformal_coverage_by_class": cov, "n_test": int(len(yte))}
    log.info("risk %s", risk_metrics)

    # ---- anomaly model ----
    Xb = np.array([fraud.behaviour_vector(a.statement) for a, _ in cases[:n_tr]])
    forest = IsolationForest(n_estimators=200, contamination="auto", random_state=3).fit(Xb)
    thr = float(np.percentile(forest.score_samples(Xb), 2))
    joblib.dump({"risk": risk, "valuer": valuer, "anomaly": fraud.AnomalyModel(forest, thr),
                 "metrics": {"property": prop_metrics, "risk": risk_metrics, "n_train": n_tr, "synthetic": True}},
                config.ARTIFACTS / "models.joblib")
    json.dump({"version": version, "property": prop_metrics, "risk": risk_metrics, "synthetic_data": True},
              open(config.ARTIFACTS / "train_metrics.json", "w"), indent=2)
    log.info(f"done in {time.time() - t0:.0f}s, model {version}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main(int(sys.argv[1]) if len(sys.argv) > 1 else N_HONEST)
