"""Cash-flow underwriting: turn a raw bank statement into a conservative, explainable income estimate."""
from __future__ import annotations

import re
import statistics as st
from calendar import monthrange
from collections import defaultdict

from pydantic import BaseModel

from . import config
from .models import Txn

CREDIT_CLASSES = [
    ("salary", re.compile(r"SALARY|PAYROLL")),
    ("loan_proceeds", re.compile(r"LOAN DISB")),
    ("self_transfer", re.compile(r"SELF TRF|OWN A/C|FD MAT|SWEEP")),
    ("refund", re.compile(r"REFUND|REVERSAL")),
    ("business", re.compile(r"UPI/CR|POS SETTL|NEFT-CR|RTGS-CR|CASH DEP|IMPS-CR")),
]
EMI_RE = re.compile(r"EMI|ACH D|NACH|LOAN REPAY")
BOUNCE_RE = re.compile(r"RETURN|BOUNCE|INSUFF")


class IncomeResult(BaseModel):
    est_monthly_income: float
    observed_months: int
    income_cv: float
    credit_mix: dict[str, float]
    statement_obligations: float
    bounces: int
    avg_balance: float
    min_balance: float
    declared_ratio: float | None
    confidence: str
    method: str
    monthly_eligible: list[float]


def classify_credit(narration: str) -> str:
    n = narration.upper()
    for label, rx in CREDIT_CLASSES:
        if rx.search(n):
            return label
    return "other"


def _complete_months(txns: list[Txn]) -> set[tuple[int, int]]:
    if not txns:
        return set()
    first, last = min(t.d for t in txns), max(t.d for t in txns)
    months = {(t.d.year, t.d.month) for t in txns}
    keep = set()
    for ym in months:
        end = monthrange(*ym)[1]
        if ym == (first.year, first.month) and first.day > 4:
            continue
        if ym == (last.year, last.month) and last.day < end - 4:
            continue
        keep.add(ym)
    return keep


def analyse(txns: list[Txn], employment: str, declared_income: float | None, bureau_obligations: float | None) -> IncomeResult:
    months = _complete_months(txns)
    by_month_credit: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    emi_by_month: dict[tuple, float] = defaultdict(float)
    mix: dict[str, float] = defaultdict(float)
    bounces = 0
    for t in txns:
        ym = (t.d.year, t.d.month)
        if t.amount > 0:
            c = classify_credit(t.narration)
            mix[c] += t.amount
            if ym in months:
                by_month_credit[ym][c] += t.amount
        else:
            if BOUNCE_RE.search(t.narration.upper()):
                bounces += 1
            elif EMI_RE.search(t.narration.upper()) and ym in months:
                emi_by_month[ym] += -t.amount
    total_credit = sum(mix.values()) or 1.0
    mix_share = {k: round(v / total_credit, 3) for k, v in mix.items()}

    ordered = sorted(months)
    if employment == "salaried":
        has_salary = any(by_month_credit[ym].get("salary", 0) > 0 for ym in ordered)
        classes = ("salary",) if has_salary else ("business",)
    else:
        classes = ("business", "salary")
    eligible = [sum(by_month_credit[ym].get(c, 0.0) for c in classes) for ym in ordered]

    if len(eligible) >= 3 and sum(eligible) > 0:
        mean, med = st.fmean(eligible), st.median(eligible)
        cv = st.pstdev(eligible) / mean if mean > 0 else 1.0
        base = min(mean, med)
        if employment == "salaried":
            est = base * (1 - min(0.10, cv))
            method = "median monthly salary credits, haircut by volatility"
        else:
            est = base * config.SELF_EMP_MARGIN * (1 - min(0.35, 0.6 * cv))
            method = f"banking-surplus: median business credits x {config.SELF_EMP_MARGIN:.0%} margin, haircut by volatility"
    else:
        est, cv, method = 0.0, 1.0, "insufficient history"

    stmt_obl = st.median(emi_by_month.values()) if emi_by_month else 0.0
    balances = [t.balance for t in txns] or [0.0]
    avg_bal = st.fmean(balances)
    conf = "high" if len(eligible) >= 9 and cv < 0.25 else "medium" if len(eligible) >= 6 else "low"
    return IncomeResult(
        est_monthly_income=round(est, 2), observed_months=len(eligible), income_cv=round(cv, 4), credit_mix=mix_share,
        statement_obligations=round(stmt_obl, 2), bounces=bounces, avg_balance=round(avg_bal, 2), min_balance=round(min(balances), 2),
        declared_ratio=round(declared_income / est, 3) if (declared_income and est > 0) else None, confidence=conf, method=method,
        monthly_eligible=[round(x, 0) for x in eligible])
