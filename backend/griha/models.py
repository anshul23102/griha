from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Txn(BaseModel):
    d: date
    amount: float            # +credit, -debit
    balance: float           # running balance after this txn
    narration: str


class Applicant(BaseModel):
    name: str
    dob: date
    pan: str
    aadhaar_last4: str       # full Aadhaar is never stored
    phone: str
    pincode: str
    gender: Literal["F", "M", "O"]   # used ONLY for fairness audit, never as a model feature
    employment: Literal["salaried", "self_employed"]
    employer: str
    declared_monthly_income: float
    city: str
    city_tier: int


class LoanRequest(BaseModel):
    product: Literal["HL", "LAP"]
    amount: float
    tenure_months: int
    co_applicant_monthly_income: float = 0.0


class PropertyInfo(BaseModel):
    property_id: str
    city: str
    tier: int
    pincode: str
    area_sqft: float
    age_years: float
    ptype: Literal["apartment", "house", "plot", "commercial"]
    declared_value: float
    circle_rate_per_sqft: float
    rera_registered: bool = True
    approved_plan: bool = True
    encumbrance: bool = False
    independent_valuations: list[float] = Field(default_factory=list, max_length=3)   # reports from independent valuers (RBI HFC Directions Annex V)
    litigation: bool = False


class BureauReport(BaseModel):
    score: Optional[int] = None      # None => thin file / no hit
    active_obligations_monthly: float = 0.0
    dpd_max_12m: int = 0
    enquiries_6m: int = 0
    writeoff: bool = False


class KycReport(BaseModel):
    pan_verified: bool = True
    aadhaar_verified: bool = True
    name_match: float = 1.0
    sanctions_hit: bool = False
    pep: bool = False
    sanctions_detail: dict | None = None   # screening result (list reference, score); internal, never shown to the applicant


class ApplicationInput(BaseModel):
    case_id: str
    applicant: Applicant
    loan: LoanRequest
    property: PropertyInfo
    statement: list[Txn]
    bureau: Optional[BureauReport] = None
    kyc: Optional[KycReport] = None
    as_of: date = date(2026, 11, 1)
    statement_source: str = "account_aggregator"
    consent: bool = True
    outage: str = "none"
    doc_issues: list[dict[str, Any]] = Field(default_factory=list)


class Reason(BaseModel):
    code: str
    text: str
    kind: Literal["policy", "risk", "fraud", "data", "property"]
    direction: Literal["adverse", "favourable", "info"] = "adverse"
    weight: Optional[float] = None


class StageEvidence(BaseModel):
    stage: str
    status: Literal["ok", "warn", "fail", "skipped"]
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    ms: float = 0.0


class Decision(BaseModel):
    case_id: str
    outcome: Literal["APPROVE", "REJECT", "REFER"]
    refer_queue: Optional[Literal["DATA", "FRAUD", "CREDIT", "PROPERTY"]] = None
    headline: str
    reasons: list[Reason] = Field(default_factory=list)
    offer: Optional[dict[str, Any]] = None
    kfs: Optional[dict[str, Any]] = None
    pd: Optional[dict[str, Any]] = None
    fraud: Optional[dict[str, Any]] = None
    path_to_yes: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[StageEvidence] = Field(default_factory=list)
    policy_version: str = ""
    policy_hash: str = ""
    model_version: str = ""
