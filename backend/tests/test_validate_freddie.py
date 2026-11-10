"""Logic tests for the real-data validation tool, using made-up rows only (no third-party data lives in the repository)."""
import numpy as np
import pandas as pd

from tools import validate_freddie as v


def _perf(rows):
    return pd.DataFrame(rows, columns=["LOAN IDENTIFIER", "PERIOD", "CURRENT LOAN DELINQUENCY STATUS", "LOAN AGE", "ZERO BALANCE CODE"])


def test_label_flags_90_plus_reo_and_credit_event_zero_balance_within_window():
    perf = _perf([
        ("A", "201601", "00", "5", None), ("A", "201602", "01", "6", None),                              # only 30 days late: not bad
        ("B", "201601", "03", "10", None),                                                              # 90+ days: bad
        ("C", "201601", "RA", "12", None),                                                              # REO: bad
        ("D", "201601", "00", "20", None), ("D", "201602", "00", "21", "03"),                           # short sale / charge-off: bad
        ("E", "201601", "00", "30", None), ("E", "201602", "04", "31", None),                           # first seen after month 24: no observation window
        ("F", "201601", "00", "8", None), ("F", "201602", "00", "9", "01"),                             # voluntary payoff: not bad
        ("G", "201601", "XX", "3", None),                                                               # not available: not bad
    ])
    y = v.label(perf)
    assert y.to_dict() == {"A": 0, "B": 1, "C": 1, "D": 1, "F": 0, "G": 0}        # E is excluded, not counted as a good loan


def test_clean_drops_freddie_not_available_codes():
    assert v.clean(pd.Series(["740", "9999", "bad"]), 900).isna().tolist() == [False, True, True]
    assert v.clean(pd.Series(["80", "999"]), 200).tolist()[0] == 80


def test_decile_table_and_spearman_detect_direction():
    rng = np.random.default_rng(0)
    x = pd.Series(rng.normal(size=5000))
    y = pd.Series((rng.random(5000) < 1 / (1 + np.exp(-(x * 1.5 - 3)))).astype(int))
    rows = v.decile_table(x, y)
    assert len(rows) == 10 and v.spearman(rows) > 0.8
    assert v.spearman(v.decile_table(-x, y)) < -0.8
