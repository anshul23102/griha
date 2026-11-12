"""The bring-your-own-data tool: a lender can retrain and validate on its own book, and a bad file is refused with a reason."""
import json

import numpy as np
import pandas as pd
import pytest

from griha import byod
from griha.features import FEATURES, MONOTONE


def _book(tmp_path, n=5000, seed=3, shift=0.0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"foir": rng.uniform(0.15, 0.7, n), "ltv": rng.uniform(0.3, 0.9, n), "bureau_score": rng.integers(560, 830, n).astype(float),
                       "income_cv": rng.uniform(0, 0.6, n), "buffer_months": rng.uniform(0, 12, n), "dpd_max_12m": rng.choice([0, 0, 0, 10, 30, 60], n),
                       "enquiries_6m": rng.poisson(1.5, n), "bounces": rng.poisson(0.4, n), "self_employed": rng.integers(0, 2, n), "age": rng.integers(24, 62, n),
                       "tenure_years": rng.integers(5, 25, n), "loan_to_income": rng.uniform(1, 6, n)})
    z = -4.2 + 3.0 * df.foir + 1.6 * df.ltv - 0.012 * (df.bureau_score - 700) + 0.02 * df.dpd_max_12m + shift
    df["default"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(int)
    df.loc[rng.choice(n, 40, replace=False), "bureau_score"] = np.nan           # thin files are allowed
    p = tmp_path / "book.csv"
    df.to_csv(p, index=False)
    return p


def test_template_has_the_columns_the_engine_uses(tmp_path):
    byod.write_template(tmp_path / "t.csv")
    assert list(pd.read_csv(tmp_path / "t.csv").columns) == FEATURES + ["default"]


def test_a_lenders_book_trains_a_separate_validated_model(tmp_path):
    out = tmp_path / "art"
    r = byod.run(_book(tmp_path), out, allow_small=True)
    assert (out / "models.joblib").exists() and (out / "byod_report.json").exists()
    assert r["model"]["auc"] > 0.68 and r["model"]["calibration_gap_mean_abs"] < 0.07
    assert json.loads((out / "train_metrics.json").read_text())["synthetic_data"] is False
    assert "GRIHA_ARTIFACTS_DIR" in r["how_to_use"] and "pd_approve_max" in r["how_to_use"]
    import joblib
    risk = joblib.load(out / "models.joblib")["risk"]
    base = dict(zip(FEATURES, [0.4, 0.7, 700, 0.2, 4, 0, 1, 0, 0, 35, 20, 3.0]))
    worse = {**base, "foir": 0.6, "dpd_max_12m": 60.0}
    assert risk.predict(worse)["pd"] > risk.predict(base)["pd"]                    # monotone: a worse debt burden and delinquency never lower risk
    assert len(MONOTONE) == len(FEATURES)


def test_bad_files_are_refused_with_a_reason(tmp_path):
    p = _book(tmp_path)
    df = pd.read_csv(p)
    df.head(1990).to_csv(tmp_path / "small.csv", index=False)
    with pytest.raises(byod.BookError, match="too few"):
        byod.load_book(tmp_path / "small.csv")                                      # under the 2,000-loan floor without --allow-small
    df.drop(columns=["ltv"]).to_csv(tmp_path / "a.csv", index=False)
    with pytest.raises(byod.BookError, match="missing columns: ltv"):
        byod.load_book(tmp_path / "a.csv", allow_small=True)
    df.assign(default=2).to_csv(tmp_path / "b.csv", index=False)
    with pytest.raises(byod.BookError, match="0 or 1"):
        byod.load_book(tmp_path / "b.csv", allow_small=True)
    df.assign(age=5).to_csv(tmp_path / "c.csv", index=False)
    with pytest.raises(byod.BookError, match="age"):
        byod.load_book(tmp_path / "c.csv", allow_small=True)
    assert byod.main(["--csv", str(tmp_path / "a.csv")]) == 2


def test_shipped_model_is_never_overwritten(tmp_path):
    from griha import config
    before = (config.ROOT / "artifacts" / "models.joblib").stat().st_mtime
    byod.run(_book(tmp_path), tmp_path / "art", allow_small=True)
    assert (config.ROOT / "artifacts" / "models.joblib").stat().st_mtime == before
