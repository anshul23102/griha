"""Bring your own data: retrain and validate the risk model on a lender's own loan book.

Why this exists. Griha ships a risk model trained on a SYNTHETIC world, because no Indian loan-level data is public. Its probabilities are therefore not
Indian default rates, and a real lender must not use them as they are. This tool is the supported way to replace them: it takes the lender's historical
loans (the twelve inputs the engine uses, plus whether the loan went bad), checks the file, fits the same monotone-constrained, calibrated, conformal model
on it, measures it out of sample, and writes a new artifact set to a separate folder. The shipped model is never overwritten.

    python -m griha.byod --template book.csv                 write an empty file with the right columns and a few illustrative rows
    python -m griha.byod --csv book.csv --out artifacts_acme  validate, train, report
    GRIHA_ARTIFACTS_DIR=artifacts_acme  (then start the API)   score with the lender's own model

The file: one row per loan, the 12 columns in griha.features.FEATURES and `default` (1 = went 90+ days past due within the observation window, else 0).
Missing values are allowed in bureau_score (thin files). Nothing leaves the machine. Property valuation and the document anomaly model are not retrained here:
they are taken from the shipped artifacts (retraining those needs the lender's valuation and statement data).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from . import config
from .features import FEATURES, MONOTONE
from .risk import RiskModel

MIN_ROWS, MIN_BADS = 2000, 100          # below this the estimates are too noisy to ship; --allow-small lowers it for tests and pilots
RANGES = {"foir": (0, 5), "ltv": (0, 2), "bureau_score": (300, 900), "income_cv": (0, 5), "buffer_months": (0, 240), "dpd_max_12m": (0, 400),
          "enquiries_6m": (0, 100), "bounces": (0, 100), "self_employed": (0, 1), "age": (18, 100), "tenure_years": (0.5, 40), "loan_to_income": (0, 100)}


class BookError(ValueError):
    pass


def write_template(path: Path) -> None:
    rows = [[0.38, 0.72, 742, 0.12, 6.0, 0, 1, 0, 0, 36, 20, 3.1], [0.52, 0.86, 655, 0.35, 2.5, 30, 3, 2, 1, 44, 15, 4.6]]
    df = pd.DataFrame(rows, columns=FEATURES)
    df["default"] = [0, 1]
    df.to_csv(path, index=False)


def load_book(path: Path, *, allow_small: bool = False) -> tuple[pd.DataFrame, np.ndarray, dict]:
    df = pd.read_csv(path)
    missing = [c for c in FEATURES + ["default"] if c not in df.columns]
    if missing:
        raise BookError(f"missing columns: {', '.join(missing)}. Run with --template to see the expected file.")
    df = df[FEATURES + ["default"]].copy()
    for c in FEATURES + ["default"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df["default"].isna().any() or not set(df["default"].unique()) <= {0, 1}:
        raise BookError("`default` must be 0 or 1 on every row")
    problems = []
    for c, (lo, hi) in RANGES.items():
        bad = int(((df[c] < lo) | (df[c] > hi)).sum())
        if bad:
            problems.append(f"{c}: {bad} value(s) outside {lo} to {hi}")
        if c != "bureau_score" and df[c].isna().any():
            problems.append(f"{c}: {int(df[c].isna().sum())} missing value(s) (only bureau_score may be empty)")
    if problems:
        raise BookError("data problems: " + "; ".join(problems))
    n, bads = len(df), int(df["default"].sum())
    if not allow_small and (n < MIN_ROWS or bads < MIN_BADS):
        raise BookError(f"{n} loans and {bads} defaults are too few for a reliable model (need at least {MIN_ROWS} and {MIN_BADS}). Use --allow-small only for a pilot.")
    if bads == 0 or bads == n:
        raise BookError("`default` has only one value")
    info = {"rows": n, "defaults": bads, "default_rate": round(bads / n, 4), "thin_file_share": round(float(df["bureau_score"].isna().mean()), 4)}
    return df[FEATURES], df["default"].to_numpy(dtype=int), info


def fit(X: pd.DataFrame, y: np.ndarray, seed: int = 11) -> tuple[RiskModel, dict]:
    """Same recipe as griha.train: bagged monotone LightGBM, isotonic calibration on a held-out slice, Mondrian conformal sets, then a clean test set."""
    X_tr, X_rest, y_tr, y_rest = train_test_split(X, y, test_size=0.38, stratify=y, random_state=seed)
    X_va, X_rest, y_va, y_rest = train_test_split(X_rest, y_rest, test_size=0.74, stratify=y_rest, random_state=seed)
    X_cal, X_te, y_cal, y_te = train_test_split(X_rest, y_rest, test_size=0.5, stratify=y_rest, random_state=seed)
    rng = np.random.default_rng(seed)
    min_leaf = int(max(20, min(80, len(X_tr) // 40)))
    boosters = []
    for k in range(5):
        idx = rng.choice(len(X_tr), size=len(X_tr), replace=True)
        params = {"objective": "binary", "learning_rate": 0.03, "num_leaves": 4, "min_data_in_leaf": min_leaf, "lambda_l2": 10.0, "feature_fraction": 0.9,
                  "bagging_fraction": 0.8, "bagging_freq": 1, "monotone_constraints": MONOTONE, "monotone_constraints_method": "advanced", "verbose": -1, "seed": 100 + k}
        boosters.append(lgb.train(params, lgb.Dataset(X_tr.iloc[idx], y_tr[idx]), 600, valid_sets=[lgb.Dataset(X_va, y_va)],
                                  callbacks=[lgb.early_stopping(40, verbose=False)]))
    raw_cal = np.mean([b.predict(X_cal) for b in boosters], axis=0)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0005, y_max=0.95).fit(raw_cal, y_cal)
    p_cal = iso.predict(raw_cal)
    qhat = []
    for lab in (0, 1):
        s = np.sort((p_cal if lab == 0 else 1 - p_cal)[y_cal == lab])
        k = min(len(s) - 1, int(np.ceil((len(s) + 1) * 0.9)) - 1)
        qhat.append(float(s[k]))
    version = hashlib.sha256(json.dumps([b.model_to_string()[:2000] for b in boosters]).encode()).hexdigest()[:12]
    risk = RiskModel(boosters, iso, qhat, version)
    p_te = risk.predict_many(X_te).mean(axis=1)
    order = np.argsort(-p_te)
    ks = float(np.max(np.abs(np.cumsum(y_te[order] == 1) / max(y_te.sum(), 1) - np.cumsum(y_te[order] == 0) / max((1 - y_te).sum(), 1))))
    cal = [{"bin": i + 1, "n": int(len(ix)), "predicted": round(float(p_te[ix].mean()), 4), "actual": round(float(y_te[ix].mean()), 4)}
           for i, ix in enumerate(np.array_split(np.argsort(p_te), 10))]
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500)).fit(X_tr, y_tr)
    metrics = {"version": version, "n_train": len(X_tr), "n_test": len(X_te), "auc": round(float(roc_auc_score(y_te, p_te)), 4), "ks": round(ks, 4),
               "brier": round(float(brier_score_loss(y_te, p_te)), 4), "logistic_auc": round(float(roc_auc_score(y_te, lr.predict_proba(X_te)[:, 1])), 4),
               "mean_predicted": round(float(p_te.mean()), 4), "mean_actual": round(float(y_te.mean()), 4), "calibration": cal,
               "calibration_gap_mean_abs": round(float(np.mean([abs(c["predicted"] - c["actual"]) for c in cal])), 4)}
    return risk, metrics


def run(csv: Path, out: Path, *, allow_small: bool = False) -> dict:
    X, y, info = load_book(csv, allow_small=allow_small)
    risk, m = fit(X, y)
    out.mkdir(parents=True, exist_ok=True)
    shipped = joblib.load(config.ROOT / "artifacts" / "models.joblib")
    synthetic_default_rate = shipped["metrics"]["risk"]["base_rate_train"]
    metrics = {**shipped["metrics"], "risk": {"baselines": {"logistic": m["logistic_auc"], "griha_gbm": m["auc"]}, "calibration": [
        {"bin": c["bin"], "n": c["n"], "predicted": c["predicted"], "actual": c["actual"]} for c in m["calibration"]], "auc": m["auc"], "ks": m["ks"], "brier": m["brier"],
        "base_rate_train": info["default_rate"], "mean_pred_test": m["mean_predicted"], "actual_test": m["mean_actual"], "n_test": m["n_test"]},
        "n_train": m["n_train"], "synthetic": False, "source": f"lender book: {info['rows']} loans"}
    joblib.dump({"risk": risk, "valuer": shipped["valuer"], "anomaly": shipped["anomaly"], "metrics": metrics}, out / "models.joblib")
    report = {"book": info, "model": m, "shipped_model_default_rate_on_its_synthetic_data": round(float(synthetic_default_rate), 4),
              "how_to_use": f"GRIHA_ARTIFACTS_DIR={out} then start the API. The policy thresholds (pd_approve_max, pd_reject_min) were tuned to the synthetic default rate: "
                            "re-set them from the lender's own loss appetite before using the model for decisions."}
    (out / "byod_report.json").write_text(json.dumps(report, indent=1))
    json.dump({"version": m["version"], "risk": metrics["risk"], "property": shipped["metrics"]["property"], "synthetic_data": False}, open(out / "train_metrics.json", "w"), indent=2)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--template", type=Path, help="write a template CSV and exit")
    ap.add_argument("--csv", type=Path, help="the lender's loan book")
    ap.add_argument("--out", type=Path, default=Path("artifacts_byod"), help="folder for the new artifact set")
    ap.add_argument("--allow-small", action="store_true", help="accept fewer than 2,000 loans / 100 defaults (pilot only)")
    a = ap.parse_args(argv)
    if a.template:
        write_template(a.template)
        print("wrote", a.template)
        return 0
    if not a.csv:
        ap.error("give --csv or --template")
    try:
        r = run(a.csv, a.out, allow_small=a.allow_small)
    except BookError as e:
        print("cannot use this file:", e, file=sys.stderr)
        return 2
    m = r["model"]
    print(f"{r['book']['rows']} loans, default rate {r['book']['default_rate']:.2%}. Out-of-sample AUC {m['auc']}, KS {m['ks']}, calibration gap {m['calibration_gap_mean_abs']:.2%}.")
    print(r["how_to_use"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
