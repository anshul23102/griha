from __future__ import annotations

import math

from . import config
from .income import IncomeResult
from .models import ApplicationInput
from .pricing import emi

FEATURES = ["foir", "ltv", "bureau_score", "income_cv", "buffer_months", "dpd_max_12m", "enquiries_6m",
            "bounces", "self_employed", "age", "tenure_years", "loan_to_income"]
#            foir ltv score cv  buf  dpd  enq  bnc  self age ten  lti
MONOTONE = [1, 1, -1, 1, -1, 1, 1, 1, 0, 0, 0, 1]

LABELS = {
    "foir": "Fixed obligations vs income",
    "ltv": "Loan-to-value",
    "bureau_score": "Bureau score",
    "income_cv": "Income volatility",
    "buffer_months": "Account balance buffer",
    "dpd_max_12m": "Recent delinquency",
    "enquiries_6m": "Recent credit enquiries",
    "bounces": "Bounced payments",
    "self_employed": "Self-employed income",
    "age": "Age",
    "tenure_years": "Tenure",
    "loan_to_income": "Loan relative to annual income",
}


def age_years(app: ApplicationInput) -> float:
    return (app.as_of - app.applicant.dob).days / 365.25


def obligations(app: ApplicationInput, inc: IncomeResult) -> float:
    b = app.bureau.active_obligations_monthly if app.bureau else 0.0
    return max(b, inc.statement_obligations)


def effective_income(app: ApplicationInput, inc: IncomeResult, co_income: float) -> float:
    return inc.est_monthly_income + config.CO_APPLICANT_HAIRCUT * co_income


def build(app: ApplicationInput, inc: IncomeResult, assessed_value: float, loan: float, tenure_months: int,
          co_income: float = 0.0) -> dict:
    est = effective_income(app, inc, co_income)
    pay = emi(loan, config.UW_RATE, tenure_months)
    obl = obligations(app, inc)
    b = app.bureau
    return {
        "foir": (pay + obl) / est if est > 0 else 9.99,
        "ltv": loan / assessed_value if assessed_value > 0 else 9.99,
        "bureau_score": float(b.score) if (b and b.score is not None) else math.nan,
        "income_cv": inc.income_cv,
        "buffer_months": inc.avg_balance / max(pay, 1.0),
        "dpd_max_12m": float(b.dpd_max_12m) if b else 0.0,
        "enquiries_6m": float(b.enquiries_6m) if b else 0.0,
        "bounces": float(inc.bounces),
        "self_employed": 1.0 if app.applicant.employment == "self_employed" else 0.0,
        "age": age_years(app),
        "tenure_years": tenure_months / 12,
        "loan_to_income": loan / (est * 12) if est > 0 else 99.0,
    }
