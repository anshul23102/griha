"""Local validation of the shipped risk model on real US mortgages (Freddie Mac Single-Family Loan-Level Dataset sample).

LEGAL: the data licence allows personal/internal research on credit performance and forbids giving the data or any Derived Product
(a model trained on it included) to third parties. So this tool (1) never trains the shipped model on the data, (2) reads the files
read-only from data-external/ (never committed, never deployed), (3) writes only aggregate figures, never loan-level rows.
Publishing even the aggregates waits for Freddie Mac's written confirmation (see docs/data-licensing.md).

It is PIPELINE validation on US loans, not Indian calibration: our model was trained on synthetic Indian-style data, and only three of
its twelve inputs exist in the US data (FICO, LTV, DTI) plus loan term.

Run (from backend/):   uv run python -m tools.validate_freddie --year 2015
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import cross_val_predict

from griha import drift
from griha.audit import AuditLog
from griha.engine import Engine
from griha.features import FEATURES

HERE = Path(__file__).resolve().parent.parent.parent / "data-external" / "freddie"
DEFAULT_CODES = {"02", "03", "09"}          # zero-balance reasons that are credit events: third-party sale, short sale/charge-off, REO disposition


def load(year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    heads = {k: (HERE / "headers" / f"{k}_data_file_header.txt").read_text().strip().split("|") for k in ("origination", "performance")}
    orig = pd.read_csv(HERE / "raw" / f"sample_orig_{year}.txt", sep="|", header=None, names=heads["origination"], dtype=str)
    pc = ["LOAN IDENTIFIER", "PERIOD", "CURRENT LOAN DELINQUENCY STATUS", "LOAN AGE", "ZERO BALANCE CODE"]
    perf = pd.read_csv(HERE / "raw" / f"sample_perf_{year}.txt", sep="|", header=None, names=heads["performance"], usecols=pc, dtype=str)
    return orig, perf


def label(perf: pd.DataFrame, months: int = 24) -> pd.Series:
    """1 if the loan was ever 90+ days delinquent (or REO) or ended in a credit-event zero balance within its first `months` of age.
    Loans with no record inside that window (some enter the file only after month 24) have no observation window and are left out, not counted as good."""
    p = perf.copy()
    p["age"] = pd.to_numeric(p["LOAN AGE"], errors="coerce")
    p = p[p["age"] <= months]
    st = p["CURRENT LOAN DELINQUENCY STATUS"].replace({"RA": "99", "XX": np.nan})
    p["dq"] = pd.to_numeric(st, errors="coerce")
    p["bad"] = (p["dq"] >= 3) | p["ZERO BALANCE CODE"].isin(DEFAULT_CODES)
    return p.groupby("LOAN IDENTIFIER")["bad"].max().astype(int)


def clean(s: pd.Series, bad_from: float) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v < bad_from)


def decile_table(x: pd.Series, y: pd.Series, q: int = 10) -> list[dict]:
    bins = pd.qcut(x.rank(method="first"), q, labels=False)
    g = pd.DataFrame({"b": bins, "x": x, "y": y}).dropna().groupby("b")
    return [{"decile": int(b) + 1, "x_mean": round(float(d["x"].mean()), 3), "default_rate": round(float(d["y"].mean()), 4), "n": int(len(d))} for b, d in g]


def spearman(rows: list[dict]) -> float:
    return round(float(pd.Series([r["decile"] for r in rows]).corr(pd.Series([r["default_rate"] for r in rows]), method="spearman")), 3)


def run(year: int) -> dict:
    orig, perf = load(year)
    y = label(perf)
    df = orig.set_index("LOAN IDENTIFIER").join(y.rename("bad"), how="inner")
    fico = clean(df["CLASSIC FICO"], 900)
    ltv = clean(df["ORIGINAL LOAN-TO-VALUE (LTV)"], 200)
    dti = clean(df["ORIGINAL DEBT-TO-INCOME (DTI) RATIO"], 200)
    term = pd.to_numeric(df["ORIGINAL LOAN TERM"], errors="coerce")
    yv = df["bad"]

    # Inputs for the shipped model. Mapping is documented and deliberately simple: DTI to FOIR, LTV to LTV, FICO rescaled from 300-850 to
    # the model's 300-900 bureau scale, term to tenure. Everything the US file does not have is filled with the median of a synthetic
    # reference population (so the model sees in-distribution values), or with the clean value at origination (no delinquency, no bounces).
    eng = Engine(audit=AuditLog(None))
    ref = drift.build_reference(eng, 400)
    med = {k: float(np.median(v)) for k, v in ref.items()}
    X = pd.DataFrame({f: np.nan for f in FEATURES}, index=df.index)
    X["foir"], X["ltv"] = dti / 100, ltv / 100
    X["bureau_score"] = 300 + (fico - 300) * 600 / 550
    X["tenure_years"] = term / 12
    for k in ("income_cv", "buffer_months", "enquiries_6m", "age", "loan_to_income"):
        X[k] = med[k]
    X["dpd_max_12m"], X["bounces"], X["self_employed"] = 0, 0, 0
    model = eng.risk
    pd_imp = pd.Series(model.predict_many(X.fillna({"foir": med["foir"], "ltv": med["ltv"], "tenure_years": med["tenure_years"]})).mean(axis=1), index=df.index)

    ok = yv.notna() & fico.notna() & ltv.notna() & dti.notna()
    exclusions = {"loans_in_sample": int(len(orig)), "no_record_in_first_24_months": int(len(orig) - len(y)),
                  "missing_fico": int(fico[yv.notna()].isna().sum()), "missing_ltv": int(ltv[yv.notna()].isna().sum()), "missing_dti": int(dti[yv.notna()].isna().sum())}
    auc = lambda s: round(float(roc_auc_score(yv[ok], s[ok])), 4)
    # Reference ceiling, local only: a plain logistic regression on the same three inputs with 5-fold cross-validation. Not shipped.
    Z = pd.DataFrame({"fico": fico, "ltv": ltv, "dti": dti})[ok]
    Z = (Z - Z.mean()) / Z.std()
    cv = cross_val_predict(LogisticRegression(max_iter=1000), Z, yv[ok], cv=5, method="predict_proba")[:, 1]

    calib = decile_table(pd_imp[ok], yv[ok])
    for r in calib:
        r["mean_predicted_pd"] = r.pop("x_mean")
    mono = {"fico": decile_table(fico[ok], yv[ok]), "ltv": decile_table(ltv[ok], yv[ok]), "dti": decile_table(dti[ok], yv[ok])}
    return {
        "dataset": f"Freddie Mac Single-Family Loan-Level Dataset, {year} vintage, 50,000-loan sample (US data; pipeline validation, not Indian calibration)",
        "label": "ever 90+ days delinquent, REO, or credit-event zero balance within first 24 months",
        "loans": int(ok.sum()), "exclusions": exclusions, "bad_rate": round(float(yv[ok].mean()), 4),
        "auc": {"shipped_model_median_imputed": auc(pd_imp), "fico_alone": auc(-fico), "ltv_alone": auc(ltv), "dti_alone": auc(dti),
                "reference_logistic_3_inputs_cv_local_only": round(float(roc_auc_score(yv[ok], cv)), 4)},
        "calibration": {"mean_predicted_pd": round(float(pd_imp[ok].mean()), 4), "observed_bad_rate": round(float(yv[ok].mean()), 4), "by_predicted_decile": calib},
        "monotonicity_check": {"fico_decile_spearman_with_default_rate": spearman(mono["fico"]), "ltv": spearman(mono["ltv"]), "dti": spearman(mono["dti"]), "tables": mono},
        "inputs_available": ["bureau_score (from FICO)", "ltv", "foir (from DTI)", "tenure_years"], "inputs_imputed_from_synthetic_medians": [k for k in FEATURES if k not in ("foir", "ltv", "bureau_score", "tenure_years")],
        "model_version": model.version,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2015)
    a = ap.parse_args()
    res = run(a.year)
    out = HERE / f"results_{a.year}.json"
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k not in ("calibration", "monotonicity_check")}, indent=2))
    print("calibration (predicted decile):")
    for r in res["calibration"]["by_predicted_decile"]:
        print(f"  d{r['decile']:>2}  predicted {r['mean_predicted_pd']:.4f}  observed {r['default_rate']:.4f}  n={r['n']}")
    print("monotonicity (Spearman of decile vs default rate):", {k: v for k, v in res["monotonicity_check"].items() if k != "tables"})
    print(f"aggregates written to {out} (local only, do not publish before Freddie Mac confirms)")
