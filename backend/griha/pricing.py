"""EMI, eligibility sizing, risk-based pricing and APR (IRR incl. fees) for the Key Fact Statement."""
from __future__ import annotations

import math

from . import config


def emi(principal: float, annual_rate: float, n: int) -> float:
    r = annual_rate / 12
    if n <= 0:
        return 0.0
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def pv_of_emi(payment: float, annual_rate: float, n: int) -> float:
    r = annual_rate / 12
    if payment <= 0 or n <= 0:
        return 0.0
    if r == 0:
        return payment * n
    return payment * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


def offer_rate(pd_mean: float, product: str) -> float:
    spread = min(0.045, 0.0025 + 0.28 * pd_mean)
    lap = 0.015 if product == "LAP" else 0.0
    return round(config.BASE_RATE + spread + lap, 4)


def max_eligible_loan(*, income: float, obligations: float, tenure_months: int, foir_cap: float,
                      ltv_cap: float, assessed_value: float, product_max: float) -> float:
    emi_room = foir_cap * income - obligations
    by_foir = pv_of_emi(emi_room, config.UW_RATE, tenure_months) if emi_room > 0 else 0.0
    by_ltv = ltv_cap * assessed_value
    best = min(by_foir, by_ltv, product_max)
    return float(max(0.0, (best // 10_000) * 10_000))


def apr(principal: float, annual_rate: float, n: int, fee: float) -> float:
    """Annualised IRR of the borrower's cash flows (disbursed net of fee, then EMIs)."""
    pay = emi(principal, annual_rate, n)
    net = principal - fee
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        pv = pay * (1 - (1 + mid) ** -n) / mid if mid > 0 else pay * n
        if pv > net:
            lo = mid
        else:
            hi = mid
    return round(lo * 12, 4)


def schedule(principal: float, rate: float, n: int) -> list[dict]:
    """Amortisation schedule (RBC Directions 2025 para 29(3)(ii)): outstanding principal, principal, interest and instalment for each month."""
    r, pay, bal, rows = rate / 12, emi(principal, rate, n), principal, []
    for k in range(1, n + 1):
        interest = bal * r
        prin = pay - interest if k < n else bal
        rows.append({"n": k, "outstanding": round(bal), "principal": round(prin), "interest": round(interest), "emi": round(prin + interest)})
        bal -= prin
    return rows


def rate_shock(principal: float, rate: float, n: int, bps: int = 25) -> dict:
    """KFS Annex I item 7: what a change of `bps` in the final rate does to the instalment (tenor kept) and to the number of instalments (instalment kept)."""
    r2 = rate + bps / 10_000
    pay = emi(principal, rate, n)
    m = r2 / 12
    inner = 1 - principal * m / pay
    n2 = math.ceil(-math.log(inner) / math.log(1 + m)) if inner > 0 else n
    return {"bps": bps, "emi_change": round(emi(principal, r2, n) - pay), "epi_count_change": int(n2 - n)}


def build_kfs(principal: float, rate: float, n: int, product: str = "HL", proposal_no: str = "") -> dict:
    k = _build_kfs(principal, rate, n, product, proposal_no)
    flags = {d["id"]: d["lender_to_set"] for d in k["other_disclosures"]}
    for d in k["hi"]["other_disclosures"]:
        d["lender_to_set"] = flags.get(d["id"], False)
    return k


def _hindi(principal, rate, n, product, fee, pay, base_disclosures=None) -> dict:
    from .pricing_hi import annex_i_hi, disclosures_hi   # imported here: pricing_hi imports this module
    from .pricing_hi import review_status
    rs = review_status()
    return {"lang": "hi", "reviewed_by_legal_translator": rs["reviewed"], "review": rs, "annex_i": annex_i_hi(principal, rate, n, product, fee, pay),
            "other_disclosures": disclosures_hi(principal, rate, n, product, fee)}


def _build_kfs(principal: float, rate: float, n: int, product: str = "HL", proposal_no: str = "") -> dict:
    fee = round(principal * config.PROC_FEE_PCT)
    pay = emi(principal, rate, n)
    total = pay * n
    return {
        "loan_amount": round(principal),
        "tenure_months": n,
        "interest_rate_annual_pct": round(rate * 100, 2),
        "rate_type": "floating, linked to benchmark",
        "emi": round(pay),
        "processing_fee": fee,
        "insurance_premium": 0,
        "total_interest": round(total - principal),
        "total_payable": round(total + fee),
        "apr_pct": round(apr(principal, rate, n, fee) * 100, 2),
        "foreclosure_charges": ("Nil: floating-rate housing loan to an individual, whatever the source of pre-closure (HFC Directions 2025 para 163(1); RBC Directions 2025 para 34(1) and (3))"
                                if product == "HL" else
                                "Nil if floating-rate and for a non-business purpose (RBC Directions 2025 para 34(1)). For a business purpose: none for upper-layer lenders, none up to ₹50 lakh for middle-layer lenders (34(2)); otherwise only as disclosed here, on the amount prepaid (34(5), (8))"),
        "grievance": "Nodal grievance redressal officer: name and contact to be inserted by the lender (RBI HFC Directions 2025 paras 142 to 144 and Digital Lending Directions 2025 para 11(ii))",
        "other_disclosures": [
            {"id": "all_in_cost", "label": "All-in cost", "value": f"APR {round(apr(principal, rate, n, fee) * 100, 2)}% including the processing fee", "basis": "HFC Directions 2025 para 132", "lender_to_set": False},
            {"id": "fee_refund", "label": "Processing fee if the loan is not sanctioned or disbursed", "value": "Lender to state the refundable amount. Illustrative: refunded in full if the loan is not disbursed", "basis": "HFC Directions 2025 para 131(1) and (2)", "lender_to_set": True},
            {"id": "penal", "label": "Penal charges for delayed repayment", "value": "Lender to set and disclose. Illustrative: 2% a year on the overdue amount, not added to the interest rate", "basis": "HFC Directions 2025 para 131(4); RBC Directions 2025 para 30(1), (4), (6): a penal charge, never penal interest, no capitalisation, levied only on the overdue amount, uniform whatever the borrower's constitution", "lender_to_set": True},
            {"id": "conversion", "label": "Charges for switching between fixed and floating rate", "value": "Lender to set and disclose. Illustrative: nil", "basis": "HFC Directions 2025 para 131(5)", "lender_to_set": True},
            {"id": "reset", "label": "Interest reset", "value": f"Floating rate linked to the benchmark (RBI repo {round(config.REPO_RATE * 100, 2)}% plus the lender's spread); it changes when the benchmark changes. Lender to state how often and how you are told", "basis": "HFC Directions 2025 para 131(6)", "lender_to_set": True},
            {"id": "rate_basis", "label": "How your rate was set", "value": f"Benchmark (RBI repo {round(config.REPO_RATE * 100, 2)}%) plus the lender's spread {round(config.LENDER_SPREAD * 100, 2)}% plus a risk premium that rises with the assessed risk of default" + (" plus 1.5% for loan against property" if product == "LAP" else "") + f". Your risk premium is {round((rate - config.BASE_RATE - (0.015 if product == 'LAP' else 0.0)) * 100, 2)}%", "basis": "RBC Directions 2025 paras 22 to 24", "lender_to_set": False},
            {"id": "no_other_fees", "label": "Charges not listed here", "value": "No fee or charge that is not in this statement can be levied at any stage without your explicit consent", "basis": "RBC Directions 2025 para 29(5)", "lender_to_set": False},
            {"id": "validity", "label": "Validity of this statement", "value": "At least three working days from the day it is given. If you accept within that time the lender is bound by these terms", "basis": "RBC Directions 2025 para 29(2)", "lender_to_set": False},
            {"id": "reset_options", "label": "When the floating rate is reset", "value": "You may choose a higher instalment, a longer tenor or both, switch to a fixed rate if the lender offers it, or prepay in part or in full at any time. Tenor extension will not cause negative amortisation. You get a statement each quarter with principal and interest recovered, instalment, instalments left and APR", "basis": "RBC Directions 2025 para 31(1) to (6)", "lender_to_set": False},
            {"id": "terms_change", "label": "If the lender changes terms to your disadvantage", "value": "You may close or switch the account within 60 days without paying any extra charge or interest", "basis": "HFC Directions 2025 para 137", "lender_to_set": False},
        ],
        "proposal_no": proposal_no,
        "validity_working_days": 3,
        "annex_i": annex_i(principal, rate, n, product, fee, pay),
        "hi": _hindi(principal, rate, n, product, fee, pay, base_disclosures=None),
        "note": "Illustrative KFS generated for the hackathon prototype; not a binding offer.",
    }


def annex_i(principal: float, rate: float, n: int, product: str, fee: int, pay: float) -> dict:
    """The standardised Key Facts Statement of the NBFC Responsible Business Conduct Directions 2025, Annex I, filled from the offer.
    Items the lender must supply carry lender_to_set; nothing is invented for them."""
    apr_pct = round(apr(principal, rate, n, fee) * 100, 2)
    shock = rate_shock(principal, rate, n)
    risk_premium = round(rate - config.BASE_RATE - (0.015 if product == "LAP" else 0.0), 4)
    L = "Lender to state"
    return {
        "source": "RBI (NBFC - Responsible Business Conduct) Directions, 2025, Annex I and para 29",
        "part1": [
            {"no": 1, "item": "Loan proposal / account number and type of loan", "value": "Home loan" if product == "HL" else "Loan against property"},
            {"no": 2, "item": "Sanctioned loan amount", "value": f"₹{round(principal):,}"},
            {"no": 3, "item": "Disbursal schedule", "value": L + " (100% upfront or in stages, and the clause of the agreement)", "lender_to_set": True},
            {"no": 4, "item": "Loan term", "value": f"{n} months ({n // 12} years)"},
            {"no": 5, "item": "Instalment details", "value": f"Equated monthly instalments: {n} of ₹{round(pay):,}; repayment starts " + L.lower(), "lender_to_set": True},
            {"no": 6, "item": "Interest rate and type", "value": f"{round(rate * 100, 2)}% a year, floating"},
            {"no": 7, "item": "Floating rate details", "value": {
                "reference_benchmark": "RBI policy repo rate", "benchmark_pct": round(config.REPO_RATE * 100, 2), "spread_pct": round((rate - config.REPO_RATE) * 100, 2),
                "final_rate_pct": round(rate * 100, 2), "reset_periodicity": L + " (months)", "impact_of_25_bps": shock}},
            {"no": 8, "item": "Fees and charges", "value": {
                "payable_to_lender": [{"name": "Processing fee", "type": "One-time", "amount": f"₹{fee:,}"}],
                "payable_to_third_party_via_lender": [{"name": "Valuation fee, insurance", "type": L, "amount": L}]}, "lender_to_set": True},
            {"no": 9, "item": "Annual percentage rate (APR)", "value": f"{apr_pct}%"},
            {"no": 10, "item": "Contingent charges", "value": {
                "penal_charges_delay": L + ". Penal charges are not added to the interest rate and are not themselves charged interest",
                "other_penal_charges": L,
                "foreclosure_charges": "Nil" if product == "HL" else "Nil for a non-business purpose; business purpose as disclosed",
                "switch_fixed_floating": L}, "lender_to_set": True},
        ],
        "part2": [
            {"no": 1, "item": "Clause of the loan agreement on recovery agents", "value": L, "lender_to_set": True},
            {"no": 2, "item": "Clause of the loan agreement on grievance redressal", "value": L, "lender_to_set": True},
            {"no": 3, "item": "Phone and email of the nodal grievance officer", "value": L, "lender_to_set": True},
            {"no": 4, "item": "Loan may be transferred to other lenders or securitised", "value": L, "lender_to_set": True},
            {"no": 5, "item": "Co-lending or outsourcing arrangement", "value": "Not applicable: no co-lender in this prototype"},
            {"no": 6, "item": "Digital loan: cooling-off period without prepayment penalty; recovery-agent LSP", "value": f"{config.COOLING_OFF_DAYS} days (illustrative; the Board sets it). No lending service provider in this prototype"},
        ],
        "apr_sheet": [
            ["Sanctioned loan amount", f"₹{round(principal):,}"], ["Loan term", f"{n} months"], ["Equated monthly instalment", f"₹{round(pay):,} x {n}"],
            ["Interest rate and type", f"{round(rate * 100, 2)}% floating"], ["Total interest over the term", f"₹{round(pay * n - principal):,}"],
            ["Fees and charges", f"₹{fee:,} (payable to the lender)"], ["Net amount disbursed", f"₹{round(principal) - fee:,}"],
            ["Total to be paid by the borrower", f"₹{round(pay * n):,}"],
            ["APR (IRR on the net amount disbursed, reducing balance)", f"{apr_pct}%"],
        ],
        "risk_premium_pct": round(risk_premium * 100, 2),
    }


def inr_short(n: float) -> str:
    if n >= 1e7:
        return f"₹{n / 1e7:.2f} Cr"
    if n >= 1e5:
        return f"₹{n / 1e5:.2f} L"
    return f"₹{n:,.0f}"
