"""Synthetic Indian mortgage applicants. Everything here is SYNTHETIC and labelled as such.

The generator keeps a hidden "true" world (true income, true default propensity) and exposes only noisy
observations (bank statement, bureau, declared values) to the engine, so models learn under realistic
information loss. Fraud typologies are injected so the fraud layer can be measured.
"""
from __future__ import annotations

import calendar
import math
from datetime import date

import numpy as np

from . import config
from .models import (Applicant, ApplicationInput, BureauReport, KycReport, LoanRequest, PropertyInfo, Txn)
from .pricing import emi

FIRST = ["Aarav", "Vivaan", "Aditya", "Rohan", "Imran", "Suresh", "Mahesh", "Karan", "Deepak", "Manoj",
         "Priya", "Anita", "Sunita", "Neha", "Kavita", "Pooja", "Ritu", "Meena", "Farah", "Lakshmi"]
LAST = ["Sharma", "Verma", "Patel", "Singh", "Khan", "Reddy", "Nair", "Gupta", "Yadav", "Joshi", "Mehta", "Das"]
EMPLOYERS = ["Acme Logistics", "Sunrise Textiles", "Bharat Agro", "Metro Hospital", "Zenith Infra",
             "Orbit Telecom", "Pragati Schools", "Kisan Foods", "City Cooperative Bank", "Vishal Retail"]
BANKS = ["HDFCBK", "SBIN", "ICICI", "BAJAJFIN", "TATACAP"]
CITIES = {1: ["Mumbai", "Pune", "Bengaluru", "Delhi NCR"], 2: ["Jaipur", "Lucknow", "Indore", "Nagpur", "Coimbatore"],
          3: ["Bhilwara", "Hisar", "Satna", "Jalna", "Bareilly"]}
TIER_RATE = {1: 9000.0, 2: 4800.0, 3: 2900.0}
TYPE_FACTOR = {"apartment": 1.0, "house": 1.1, "plot": 0.55, "commercial": 1.35}
PTYPES = list(TYPE_FACTOR)
RING_PHONES = [f"98000000{i:02d}" for i in range(8)]
RING_PROPS = [f"PRP-RING-{i}" for i in range(6)]
FRAUD_TYPES = ["edit", "dressing", "identity", "inflate_income", "ring"]


def _pin_table() -> dict[str, float]:
    rng = np.random.default_rng(7)
    return {f"{100000 + t * 100000 + i * 37}": float(np.exp(rng.normal(0, 0.25)))
            for t in (1, 2, 3) for i in range(20)}


PIN_INDEX = _pin_table()
PINS_BY_TIER = {t: [p for p in PIN_INDEX if p.startswith(str(1 + t))] for t in (1, 2, 3)}


def market_rate(tier: int, pin: str, age: float, ptype: str) -> float:
    return TIER_RATE[tier] * PIN_INDEX[pin] * TYPE_FACTOR[ptype] * (1 - 0.012 * min(age, 40))


def _gen_statement(rng, true_income, employment, employer, obligations, vol, living_frac, stress,
                   as_of: date, months=12) -> list[Txn]:
    y, m = as_of.year, as_of.month
    seq = []
    for k in range(months, 0, -1):
        mm = m - k
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        seq.append((yy, mm))
    balance = float(true_income * rng.uniform(0.3, 2.5))
    out: list[Txn] = []
    phase = rng.uniform(0, 6.28)
    for (yy, mm) in seq:
        days = calendar.monthrange(yy, mm)[1]
        events: list[tuple[int, float, str]] = []
        if employment == "salaried":
            amt = true_income * rng.normal(1, 0.015)
            events.append((int(rng.integers(1, 6)), amt, f"NEFT-SALARY-{employer.upper()}"))
            if rng.random() < 0.05:
                events.append((int(rng.integers(10, 25)), true_income * rng.uniform(0.3, 1.0), "NEFT-SALARY ARREARS"))
            turnover_out = 0.0
        else:
            season = 1 + 0.25 * math.sin(2 * math.pi * mm / 12 + phase)
            turnover = (true_income / config.SELF_EMP_MARGIN) * season * float(np.exp(rng.normal(0, vol)))
            n = int(rng.integers(8, 24))
            parts = rng.dirichlet(np.ones(n)) * turnover
            for part in parts:
                kind = rng.choice(["UPI/CR/CUST", "NEFT-CR-CUSTOMER", "POS SETTL", "CASH DEP"], p=[.5, .2, .2, .1])
                events.append((int(rng.integers(1, days + 1)), float(part), f"{kind} {int(rng.integers(1000, 9999))}"))
            turnover_out = turnover * 0.70
            for _ in range(int(rng.integers(2, 5))):
                events.append((int(rng.integers(1, days + 1)), -turnover_out / 3.0, f"NEFT-DR-SUPPLIER {int(rng.integers(100, 999))}"))
        if rng.random() < 0.6:
            events.append((int(rng.integers(1, days + 1)), float(rng.uniform(500, 3000)), "UPI/CR/FRIEND"))
        # obligations
        if obligations > 0:
            bank = BANKS[int(rng.integers(0, len(BANKS)))]
            events.append((int(rng.integers(5, 9)), -obligations, f"ACH D- LOAN REPAY - {bank}"))
        # living expenses
        living = true_income * living_frac
        for part in rng.dirichlet(np.ones(int(rng.integers(8, 15)))) * living:
            events.append((int(rng.integers(1, days + 1)), -float(part), f"UPI/DR/{int(rng.integers(10000, 99999))}"))
        events.sort(key=lambda e: (e[0], -e[1]))
        bounced = False
        for day, amt, narr in events:
            if amt < 0:
                avail = max(balance - 500, 0)
                if -amt > avail:
                    if "LOAN REPAY" in narr and rng.random() < stress:
                        bounced = True
                        amt, narr = -590.0, "RETURN CHGS-INSUFF FUNDS"
                        amt = -min(590.0, avail)
                    else:
                        amt = -avail * 0.95
                        if amt > -1:
                            continue
            balance += amt
            out.append(Txn(d=date(yy, mm, day), amount=round(amt, 2), balance=round(balance, 2), narration=narr))
        _ = bounced
    return out


def _recompute_balances(txns: list[Txn], start: float) -> list[Txn]:
    bal, res = start, []
    for t in sorted(txns, key=lambda x: (x.d, -x.amount)):
        bal += t.amount
        res.append(Txn(d=t.d, amount=t.amount, balance=round(bal, 2), narration=t.narration))
    return res


def _valuer_reports(seed: int, loan: float, declared: float) -> list[float]:
    """SYNTHETIC independent valuer reports, one per report the Directions require at this loan size (Annex V paras 1.5 and 1.6).
    Drawn from a separate generator so adding them never shifts the random streams the models were trained on."""
    need = 2 if loan >= 7_500_000 else 1 if loan >= 5_000_000 else 0
    r = np.random.default_rng(seed + 10_000_019)
    return [round(declared * float(np.exp(r.normal(0, 0.03)))) for _ in range(need)]


def make_case(seed: int, fraud: str | None | bool = False) -> tuple[ApplicationInput, dict]:
    """Return (application, hidden truth). fraud=False/None → honest; fraud=True → random typology; str → that one."""
    rng = np.random.default_rng(seed)
    as_of = date(*config.AS_OF_DEFAULT)
    if fraud is True:
        fraud = FRAUD_TYPES[int(rng.integers(0, len(FRAUD_TYPES)))]
    fraud = fraud or None

    age = int(rng.integers(24, 59))
    tier = int(rng.choice([1, 2, 3], p=[0.2, 0.45, 0.35]))
    city = CITIES[tier][int(rng.integers(0, len(CITIES[tier])))]
    pin = PINS_BY_TIER[tier][int(rng.integers(0, len(PINS_BY_TIER[tier])))]
    ptype = str(rng.choice(PTYPES, p=[0.55, 0.30, 0.10, 0.05]))
    area = float(rng.uniform(450, 2200))
    age_prop = float(rng.uniform(0, 30))
    rate_sqft = market_rate(tier, pin, age_prop, ptype)
    market_value = area * rate_sqft * float(np.exp(rng.normal(0, 0.06)))
    declared_value = market_value * float(np.exp(rng.normal(0, 0.05)))
    if rng.random() < 0.04 or fraud == "edit":
        declared_value *= float(rng.uniform(1.25, 1.5))
    circle = rate_sqft * 0.65 * float(np.exp(rng.normal(0, 0.1)))

    product = "LAP" if rng.random() < 0.25 else "HL"
    ltv_req = float(rng.uniform(0.5, 0.9)) if product == "HL" else float(rng.uniform(0.4, 0.65))
    loan = min(max(ltv_req * declared_value, 300_000.0), 15_000_000.0)
    loan = round(loan / 10_000) * 10_000
    tenure = int(rng.choice([120, 180, 240, 300, 360] if product == "HL" else [60, 120, 180]))
    tenure = int(max(60, min(tenure, (68 - age) * 12 // 12 * 12)))
    u = float(np.clip(rng.beta(4, 6) * 0.55 + 0.10, 0.1, 0.95))   # true EMI-to-income
    true_income = max(emi(loan, 0.10, tenure) / u, 12_000.0)

    employment = "salaried" if rng.random() < 0.40 else "self_employed"
    vol = 0.06 if employment == "salaried" else float(rng.uniform(0.10, 0.55))
    employer = EMPLOYERS[int(rng.integers(0, len(EMPLOYERS)))]
    obligation_frac = float(rng.choice([0.0, 0.0, 0.05, 0.12, 0.2, 0.3]))
    obligations = true_income * obligation_frac
    living_frac = float(rng.uniform(0.22, 0.48))
    stress = float(np.clip((obligations / true_income + living_frac + u - 0.9) * 2 + rng.normal(0, 0.1), 0, 0.8))

    stmt = _gen_statement(rng, true_income, employment, employer, obligations, vol, living_frac, stress, as_of)

    first, last = FIRST[int(rng.integers(0, len(FIRST)))], LAST[int(rng.integers(0, len(LAST)))]
    gender = str(rng.choice(["F", "M"], p=[0.28, 0.72]))
    dob = date(as_of.year - age, int(rng.integers(1, 13)), int(rng.integers(1, 28)))
    phone = f"9{int(rng.integers(100000000, 999999999))}"
    pan = "".join(chr(65 + int(rng.integers(0, 26))) for _ in range(5)) + f"{int(rng.integers(1000, 9999))}" + chr(65 + int(rng.integers(0, 26)))
    prop_id = f"PRP-{seed:07d}"
    declared_income = true_income * float(np.exp(rng.normal(0.03, 0.06)))

    kyc = KycReport(pan_verified=bool(rng.random() > 0.01), aadhaar_verified=bool(rng.random() > 0.02),
                    name_match=float(np.clip(rng.beta(30, 1.5), 0.6, 1.0)),
                    sanctions_hit=bool(rng.random() < 0.002), pep=bool(rng.random() < 0.005))
    # bureau: score correlated with latent creditworthiness
    q = -stress * 1.5 + rng.normal(0, 0.6)
    score = int(np.clip(735 + 45 * q + rng.normal(0, 22), 300, 900))
    thin = rng.random() < 0.08
    dpd = int(rng.choice([0, 10, 30, 60, 90], p=[0.86, 0.06, 0.04, 0.025, 0.015]))
    if score < 640 and rng.random() < 0.4 and dpd == 0:
        dpd = 30
    bureau = BureauReport(score=None if thin else score, active_obligations_monthly=round(obligations * float(rng.uniform(0.95, 1.05)), 0),
                          dpd_max_12m=dpd, enquiries_6m=int(rng.poisson(1.2 + 3 * stress)), writeoff=bool(rng.random() < 0.01))

    if fraud == "edit":
        idx = [i for i, t in enumerate(stmt) if t.amount > 5000]
        for i in rng.choice(idx, size=min(len(idx), int(rng.integers(2, 5))), replace=False):
            stmt[i] = Txn(d=stmt[i].d, amount=round(stmt[i].amount * float(rng.uniform(1.8, 2.6)), 2),
                          balance=stmt[i].balance, narration=stmt[i].narration)
    elif fraud == "dressing":
        start = stmt[0].balance - stmt[0].amount
        extra = []
        last_month = stmt[-1].d.replace(day=1)
        base = true_income / (config.SELF_EMP_MARGIN if employment == "self_employed" else 1.0)
        for j in range(int(rng.integers(4, 8))):
            amt = float(round(base * rng.uniform(0.8, 1.5), -4))
            d0 = date(last_month.year, last_month.month, int(rng.integers(2, 27)))
            nm = f"NEFT-CR-{LAST[int(rng.integers(0, len(LAST)))].upper()} TRADERS"
            extra.append(Txn(d=d0, amount=amt, balance=0, narration=nm))
            if j % 2 == 0:   # round-trip: same amount leaves within days
                extra.append(Txn(d=date(d0.year, d0.month, min(28, d0.day + int(rng.integers(1, 4)))), amount=-amt * 0.99, balance=0, narration=nm.replace("CR", "DR")))
        stmt = _recompute_balances(stmt + extra, start)
    elif fraud == "identity":
        kyc.name_match = float(rng.uniform(0.5, 0.8))
        phone = RING_PHONES[int(rng.integers(0, len(RING_PHONES)))]
    elif fraud == "inflate_income":
        declared_income = true_income * float(rng.uniform(1.8, 2.6))
    elif fraud == "ring":
        phone = RING_PHONES[int(rng.integers(0, len(RING_PHONES)))]
        prop_id = RING_PROPS[int(rng.integers(0, len(RING_PROPS)))]

    app = ApplicationInput(
        case_id=f"C{seed:07d}",
        applicant=Applicant(name=f"{first} {last}", dob=dob, pan=pan, aadhaar_last4=f"{int(rng.integers(0, 9999)):04d}",
                            phone=phone, pincode=pin, gender=gender, employment=employment, employer=employer,
                            declared_monthly_income=round(declared_income), city=city, city_tier=tier),
        loan=LoanRequest(product=product, amount=float(loan), tenure_months=tenure),
        property=PropertyInfo(property_id=prop_id, city=city, tier=tier, pincode=pin, area_sqft=round(area), age_years=round(age_prop, 1),
                              ptype=ptype, declared_value=round(declared_value), circle_rate_per_sqft=round(circle),
                              rera_registered=bool(rng.random() > 0.15), approved_plan=bool(rng.random() > 0.04),
                              encumbrance=bool(rng.random() < 0.04), litigation=bool(rng.random() < 0.01),
                              independent_valuations=_valuer_reports(seed, float(loan), round(declared_value))),
        statement=stmt, bureau=bureau, kyc=kyc, as_of=as_of)

    # hidden truth → default label
    foir_true = (emi(loan, 0.115, tenure) + obligations) / true_income
    ltv_true = loan / market_value
    bounces = sum("RETURN" in t.narration for t in stmt)
    logit = (-4.2 + 4.5 * max(0.0, foir_true - 0.35) + 3.0 * (ltv_true - 0.7) - 0.011 * ((score if not thin else 680) - 720)
             + 1.4 * vol + 0.9 * (dpd >= 30) + 0.10 * bureau.enquiries_6m + 0.35 * min(bounces, 3)
             + 0.25 * (employment == "self_employed") + float(rng.normal(0, 0.45)))
    p_def = 1 / (1 + math.exp(-logit))
    default = int(rng.random() < p_def) if not fraud else int(rng.random() < 0.8)
    truth = {"default": default, "p_default": p_def, "fraud": fraud, "true_income": true_income,
             "market_value": market_value, "foir_true": foir_true, "ltv_true": ltv_true}
    return app, truth
