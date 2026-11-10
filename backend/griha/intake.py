"""Real application intake. The applicant supplies applicant, loan and property facts; bank, bureau, KYC and land-record
data come from SIMULATED adapters that are deterministic per applicant (seeded from PAN and phone), so every run replays."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from . import config, sanctions
from .models import Applicant, ApplicationInput, BureauReport, KycReport, LoanRequest, PropertyInfo, Txn
from .synth import CITIES, PIN_INDEX, PINS_BY_TIER, PTYPES, _gen_statement, market_rate

PAN_RX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
PHONE_RX = re.compile(r"^[6-9][0-9]{9}$")
WATCHLIST_FIXTURE = {"vikram sanctioned", "test watchlist"}   # demo names that always hit, so the referral path can be shown; the real screen is griha/sanctions.py
CITY_TIER = {c: t for t, cs in CITIES.items() for c in cs}


class IntakeForm(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    dob: date
    pan: str
    phone: str
    gender: Literal["F", "M", "O"]
    employment: Literal["salaried", "self_employed"]
    employer: str = Field(min_length=2, max_length=80)
    monthly_income: float = Field(ge=8_000, le=2_000_000)
    existing_emi: float = Field(default=0, ge=0, le=1_000_000)
    city: str
    pincode: str
    product: Literal["HL", "LAP"]
    amount: float = Field(ge=100_000, le=50_000_000)
    tenure_months: int = Field(ge=12, le=420)
    co_applicant_monthly_income: float = Field(default=0, ge=0, le=2_000_000)
    property_type: Literal["apartment", "house", "plot", "commercial"]
    area_sqft: float = Field(ge=100, le=20_000)
    property_age_years: float = Field(ge=0, le=100)
    declared_value: float = Field(ge=100_000, le=500_000_000)
    survey_no: str = Field(min_length=3, max_length=40)
    consent: bool
    statement_source: Literal["linked", "uploaded"] = "linked"
    bank_profile: Literal["steady", "variable", "irregular"] = "steady"
    document_id: Optional[str] = Field(default=None, pattern="^D-[0-9A-F]{32}$")
    simulate_outage: Literal["none", "bureau", "bureau_flaky", "kyc"] = "none"
    independent_valuations: list[float] = Field(default_factory=list, max_length=3)      # values from independent valuers' reports, if the applicant has them

    @field_validator("name", "employer", "survey_no", "city", mode="after")
    @classmethod
    def _clean_text(cls, v):
        """No control or bidirectional-override characters: they hide text from reviewers and corrupt the audit trail."""
        bad = [c for c in v if unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co") or c in "<>"]
        if bad:
            raise ValueError("Remove special characters from this field")
        return " ".join(v.split())

    @field_validator("independent_valuations", mode="after")
    @classmethod
    def _valuations(cls, v):
        for x in v:
            if not (100_000 <= x <= 500_000_000):
                raise ValueError("Each valuation must be between Rs 1 lakh and Rs 50 crore")
        return v

    @field_validator("pan", mode="before")
    @classmethod
    def _pan(cls, v):
        v = str(v).strip().upper()
        if not PAN_RX.match(v):
            raise ValueError("PAN must look like ABCDE1234F")
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, v):
        v = re.sub(r"\D", "", str(v))[-10:]
        if not PHONE_RX.match(v):
            raise ValueError("Enter a 10-digit mobile number starting 6 to 9")
        return v

    @model_validator(mode="after")
    def _checks(self):
        as_of = date(*config.AS_OF_DEFAULT)
        age = (as_of - self.dob).days / 365.25
        if age < 21:
            raise ValueError("Applicant must be at least 21")
        if age > 70:
            raise ValueError("Applicant must be 70 or younger")
        if not self.consent:
            raise ValueError("Consent is required to fetch bank, bureau and property records")
        if self.city not in CITY_TIER:
            raise ValueError("Choose a city from the list")
        if self.pincode not in PIN_INDEX or not self.pincode.startswith(str(1 + CITY_TIER[self.city])):
            raise ValueError("Choose a PIN code from the list for this city")
        if self.existing_emi > self.monthly_income:
            raise ValueError("Existing EMIs cannot exceed monthly income")
        if self.statement_source == "uploaded" and not self.document_id:
            raise ValueError("Upload a statement PDF or choose the linked-account option")
        return self


def _h(*parts: str) -> int:
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16)


def build_application(f: IntakeForm, case_id: str, statement: Optional[list[Txn]] = None, doc_issues: Optional[list] = None,
                      source: Optional[str] = None) -> ApplicationInput:
    as_of = date(*config.AS_OF_DEFAULT)
    tier = CITY_TIER[f.city]
    seed = _h(f.pan, f.phone) % (2 ** 32)
    rng = np.random.default_rng(seed)
    ratio = f.existing_emi / f.monthly_income

    if statement is None:   # simulated Account Aggregator pull
        vol = {"steady": 0.06 if f.employment == "salaried" else 0.14, "variable": 0.28, "irregular": 0.5}[f.bank_profile]
        true_income = f.monthly_income * float(rng.uniform(0.93, 1.0))
        stress = float(np.clip((ratio + 0.35 - 0.6) * 1.5, 0, 0.6))
        statement = _gen_statement(rng, true_income, f.employment, f.employer, f.existing_emi, vol, float(rng.uniform(0.25, 0.4)), stress, as_of)
        source = "simulated Account Aggregator link"

    thin = rng.random() < 0.06
    score = int(np.clip(745 - 140 * ratio + rng.normal(0, 32), 380, 880))
    dpd = int(rng.choice([0, 10, 30, 60, 90], p=[0.92, 0.04, 0.025, 0.01, 0.005]))
    bureau = BureauReport(score=None if thin else score, active_obligations_monthly=f.existing_emi, dpd_max_12m=dpd,
                          enquiries_6m=int(rng.poisson(1.1)), writeoff=bool(rng.random() < 0.004))
    if f.simulate_outage == "kyc":
        kyc = None
    else:
        scr = sanctions.screen(f.name, f.dob.year)
        real_hit = any(m["dob_year_consistent"] is not False or m["score"] >= 0.97 for m in scr["matches"])   # a contradicting birth year only downgrades a weaker name match
        demo_hit = f.name.strip().lower() in WATCHLIST_FIXTURE
        kyc = KycReport(pan_verified=True, aadhaar_verified=True, name_match=1.0, sanctions_hit=real_hit or demo_hit, pep=False,
                        sanctions_detail={"source": "UN Security Council Consolidated List", "list_date": scr["list_date"], "entries_checked": scr["checked"],
                                          "matches": scr["matches"], "demo_fixture": demo_hit})

    ph = _h("prop", f.survey_no.upper(), f.pincode)
    pr = np.random.default_rng(ph % (2 ** 32))
    circle = market_rate(tier, f.pincode, f.property_age_years, f.property_type) * 0.65
    prop = PropertyInfo(property_id=f"PRP-{ph % 10**8:08d}", city=f.city, tier=tier, pincode=f.pincode, area_sqft=f.area_sqft,
                        age_years=f.property_age_years, ptype=f.property_type, declared_value=f.declared_value,
                        circle_rate_per_sqft=round(circle), rera_registered=bool(pr.random() > 0.12), approved_plan=bool(pr.random() > 0.04),
                        encumbrance=bool(pr.random() < 0.05), litigation=bool(pr.random() < 0.015),
                        independent_valuations=list(f.independent_valuations))
    return ApplicationInput(
        case_id=case_id,
        applicant=Applicant(name=f.name.strip(), dob=f.dob, pan=f.pan, aadhaar_last4=f"{_h('aad', f.pan) % 10000:04d}", phone=f.phone,
                            pincode=f.pincode, gender=f.gender, employment=f.employment, employer=f.employer.strip(),
                            declared_monthly_income=f.monthly_income, city=f.city, city_tier=tier),
        loan=LoanRequest(product=f.product, amount=f.amount, tenure_months=f.tenure_months,
                         co_applicant_monthly_income=f.co_applicant_monthly_income),
        property=prop, statement=statement, bureau=None if f.simulate_outage == "bureau" else bureau, kyc=kyc, as_of=as_of,
        statement_source=source or "simulated Account Aggregator link", doc_issues=doc_issues or [], outage=f.simulate_outage)


def reference(policy) -> dict:
    return {
        "cities": [{"name": c, "tier": t, "pins": PINS_BY_TIER[t][:8]} for t, cs in CITIES.items() for c in cs],
        "property_types": PTYPES,
        "products": {p: {"max_tenure_years": policy.tenure_cap_years(p), "ltv_caps": policy.data["ltv_caps"][p]} for p in ("HL", "LAP")},
        "limits": {"min_loan": policy.params["min_loan"], "max_loan": policy.params["max_loan"]},
        "as_of": date(*config.AS_OF_DEFAULT).isoformat(),
        "screening_fixture": sorted(WATCHLIST_FIXTURE),
    }
