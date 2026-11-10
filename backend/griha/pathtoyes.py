"""Path to Yes: counterfactual search over levers the applicant can actually pull."""
from __future__ import annotations

from .models import ApplicationInput

NON_ACTIONABLE = {"AML_SANCTIONS", "KYC_PAN", "WRITEOFF", "TITLE_LITIGATION"}


def path_to_yes(engine, app: ApplicationInput, decision, max_options: int = 4) -> list[dict]:
    if decision.outcome == "APPROVE":
        return []
    codes = {r.code for r in decision.reasons if r.kind in ("policy", "fraud")}
    if decision.refer_queue == "FRAUD" or codes & NON_ACTIONABLE:
        return [{"lever": "none", "actionable": False,
                 "message": "This outcome does not depend on the loan terms, so changing the amount or tenure will not change it. An officer will contact you."}]
    amt, ten = app.loan.amount, app.loan.tenure_months
    tenure_cap = int(engine.policy.tenure_cap_years(app.loan.product) * 12)
    found: list[dict] = []

    def try_it(label, lever, change, **ov):
        d = engine.underwrite(app, overrides=ov, record=False)
        if d.outcome == "APPROVE":
            found.append({"lever": lever, "actionable": True, "message": label, "change": change, "offer": d.offer})
            return True
        return False

    # 1. smaller loan
    for frac in (0.9, 0.8, 0.7, 0.6, 0.5, 0.4):
        new = round(amt * frac / 10_000) * 10_000
        if try_it(f"Reduce the loan to {new:,.0f} ({int(frac * 100)}% of the request)", "reduce_amount", {"loan_amount": new}, loan_amount=new):
            break
    # 2. longer tenure
    for t in range(ten + 60, tenure_cap + 1, 60):
        if try_it(f"Extend the tenure to {t // 12} years", "extend_tenure", {"tenure_months": t}, tenure_months=t):
            break
    # 3. co-applicant
    for co in (10_000, 20_000, 30_000, 50_000):
        if try_it(f"Add a co-applicant earning {co:,.0f} a month", "co_applicant", {"co_applicant_monthly_income": co}, co_applicant_monthly_income=co):
            break
    return found[:max_options] or [{"lever": "none", "actionable": False,
                                    "message": "No single change to amount, tenure or co-applicant leads to approval. A credit officer will review."}]
