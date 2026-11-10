"""Instant pre-qualification: how much can I borrow? Same policy numbers as the engine, no case created."""
from __future__ import annotations

from . import config, pricing
from .policy import Policy


def quick(policy: Policy, *, product: str, income: float, obligations: float, co_income: float, tenure_months: int, property_value: float) -> dict:
    p = policy.params
    tenure = min(tenure_months, int(policy.tenure_cap_years(product) * 12))
    eff_income = income + config.CO_APPLICANT_HAIRCUT * co_income
    best, best_cap, parts = 0.0, 0.0, {}
    for band in policy.data["ltv_caps"][product]:
        pm = min(p["max_loan"], band["up_to"] or p["max_loan"])
        cand = pricing.max_eligible_loan(income=eff_income, obligations=obligations, tenure_months=tenure, foir_cap=p["foir_cap"],
                                         ltv_cap=band["cap"], assessed_value=property_value, product_max=pm)
        if cand > best:
            best, best_cap = cand, band["cap"]
            room = p["foir_cap"] * eff_income - obligations
            parts = {"by_income": pricing.pv_of_emi(room, config.UW_RATE, tenure) if room > 0 else 0.0, "by_property": band["cap"] * property_value, "by_product": float(pm)}
    binding = min(parts, key=parts.get) if parts else "by_income"
    lo, hi = pricing.offer_rate(0.02, product), pricing.offer_rate(0.08, product)
    return {"max_loan": best, "binding": binding, "ltv_cap": best_cap, "foir_cap": p["foir_cap"], "tenure_months": tenure,
            "tenure_capped": tenure < tenure_months, "stress_rate_pct": round(config.UW_RATE * 100, 2),
            "rate_range_pct": [round(lo * 100, 2), round(hi * 100, 2)],
            "emi_range": [round(pricing.emi(best, lo, tenure)), round(pricing.emi(best, hi, tenure))] if best else [0, 0],
            "min_loan": p["min_loan"], "eligible": best >= p["min_loan"], "effective_income": round(eff_income),
            "note": "Indicative only: income is taken as stated and is verified from the bank statement in a real application."}
