"""Loan servicing duties that follow a sanction, built from the primary text of two RBI documents:

* NBFC Responsible Business Conduct Directions 2025 (RBI/DOR/2025-26/362)
    para 31(6)  a statement at the end of each quarter: principal and interest recovered to date, EMI, EMIs left, annualised rate / APR for the whole tenor
    paras 35-41 release of original property documents and charge satisfaction within 30 days of full repayment; the borrower chooses where to collect them; a
                reason for any delay; compensation of Rs 5,000 for each day of delay attributable to the lender; 60 days instead of 30 where documents are lost or damaged
    paras 93-101 recovery agents: due diligence and verified antecedents, notice and authorisation letter, details published, no harassment, no calls before
                8:00 a.m. or after 7:00 p.m., no persistent calling
* RBI Housing Finance Companies Directions 2025 para 170: the same for HFCs, plus a recording of recovery calls made with the borrower's knowledge, contact only
  with the borrower or guarantor, no calls on bereavement, wedding or festival days, and the time and number of calls documented.

Nothing here is a loan account: no loan is disbursed in this prototype. The statement is computed from the offer's own schedule as if the loan had been disbursed on
acceptance, and is labelled so. The closure and recovery tools are the rules and the arithmetic, enforced on the data a lender would enter.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import pricing

IST = ZoneInfo("Asia/Kolkata")
RELEASE_DAYS = 30                 # RBC para 35
RELEASE_DAYS_DAMAGED = 60         # RBC para 40: a further 30 days where documents are lost or damaged
COMPENSATION_PER_DAY = 5000       # RBC para 39
CALL_FROM_HOUR, CALL_TO_HOUR = 8, 19      # RBC para 100; HFC para 170(6)(i)(e)
MAX_CONTACTS_PER_DAY = 3          # INTERNAL: the Directions forbid "persistently calling" without a number; this is our reading, for the lender to set


def add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    day = min(d.day, [31, 29 if (d.year + y) % 4 == 0 and ((d.year + y) % 100 != 0 or (d.year + y) % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo])
    return date(d.year + y, mo + 1, day)


def quarterly_statements(kfs: dict, disbursed_on: date, months_elapsed: int) -> dict:
    """Statements at the end of each completed quarter, from the KFS's own terms. RBC Directions 2025 para 31(6)."""
    principal, n = float(kfs["loan_amount"]), int(kfs["tenure_months"])
    rate = float(kfs["interest_rate_annual_pct"]) / 100
    rows = pricing.schedule(principal, rate, n)
    emi = float(kfs["emi"])
    out = []
    for q in range(1, min(months_elapsed, n) // 3 + 1):
        m = 3 * q
        paid = rows[:m]
        out.append({"quarter": q, "period_end": add_months(disbursed_on, m).isoformat(), "emis_paid": m, "emis_left": n - m,
                    "principal_recovered": round(sum(r["principal"] for r in paid)), "interest_recovered": round(sum(r["interest"] for r in paid)),
                    "outstanding_principal": round(rows[m]["outstanding"]) if m < n else 0, "emi": round(emi), "interest_rate_pct": kfs["interest_rate_annual_pct"],
                    "apr_pct": kfs["apr_pct"]})
    return {"illustrative": True, "assumed_disbursal": disbursed_on.isoformat(), "tenure_months": n, "loan_amount": round(principal), "statements": out,
            "basis": "RBC Directions 2025 para 31(6)",
            "note": "No loan is disbursed in this prototype. The statements are what the borrower would receive, computed from the offer's schedule as if the loan were disbursed on the date shown."}


@dataclass
class Closure:
    repaid_on: date
    damaged: bool = False
    released_on: date | None = None
    collection_place: str = "the branch or office that serviced the account"


def closure_status(c: Closure, today: date) -> dict:
    """Release of original property documents and charge satisfaction. RBC Directions 2025 paras 35 to 41."""
    due = c.repaid_on + timedelta(days=RELEASE_DAYS_DAMAGED if c.damaged else RELEASE_DAYS)
    end = c.released_on or today
    delay = max(0, (end - due).days)
    return {"repaid_on": c.repaid_on.isoformat(), "release_due_by": due.isoformat(), "released_on": c.released_on.isoformat() if c.released_on else None,
            "status": "released" if c.released_on else ("overdue" if delay else "within time"), "days_late": delay, "compensation_inr": delay * COMPENSATION_PER_DAY,
            "borrower_collects_at": c.collection_place,
            "must_do": ["Release all original documents and remove charges registered with any registry within the period (para 35)",
                        "Let the borrower choose the office where they collect them (para 36)",
                        "Tell the borrower the reason for any delay beyond the period (para 39)",
                        "Pay Rs 5,000 for each day of delay attributable to the lender (para 39), without prejudice to other compensation (para 41)",
                        "If documents are lost or damaged: help get certified copies at the lender's cost and pay the compensation; 60 days in all (para 40)"],
            "legal_heirs": "On the death of a sole or joint borrower the documents go to the legal heirs under a procedure the lender must publish (para 38)."}


def check_contact(*, at: datetime, agent_ok: bool, agent_problems: list[str], target: str, recorded_notice: bool, sensitive_occasion: bool,
                  contacts_today: int, channel: str) -> dict:
    """Would this recovery contact break a rule? Every reason cites its paragraph. Local time in India decides the calling window."""
    local = at.astimezone(IST) if at.tzinfo else at.replace(tzinfo=IST)
    v: list[dict] = []
    if not (CALL_FROM_HOUR <= local.hour < CALL_TO_HOUR):
        v.append({"rule": "HOURS", "text": f"Contact at {local:%H:%M} IST is outside 8:00 a.m. to 7:00 p.m.", "cite": "RBC Directions 2025 para 100; HFC Directions 2025 para 170(6)(i)(e)"})
    if not agent_ok:
        v.append({"rule": "AGENT", "text": "The recovery agent is not properly empanelled: " + ("; ".join(agent_problems) or "unknown agent"),
                  "cite": "RBC Directions 2025 paras 94 to 96; HFC Directions 2025 para 170(2), (4)"})
    if target not in ("borrower", "guarantor"):
        v.append({"rule": "TARGET", "text": "Recovery contact is only with the borrower or a guarantor, never relatives, referees or friends.", "cite": "HFC Directions 2025 para 170(6)(i)(m); RBC para 100"})
    if channel in ("call", "phone") and not recorded_notice:
        v.append({"rule": "RECORDING", "text": "Calls must be recorded with the borrower's knowledge: tell them the conversation is being recorded.", "cite": "HFC Directions 2025 para 170(4)(vi)"})
    if sensitive_occasion:
        v.append({"rule": "OCCASION", "text": "Avoid bereavement, weddings, festivals and similar occasions.", "cite": "HFC Directions 2025 para 170(6)(i)(k)"})
    if contacts_today >= MAX_CONTACTS_PER_DAY:
        v.append({"rule": "PERSISTENT", "text": f"{contacts_today} contacts already today: persistent calling is forbidden. The limit of {MAX_CONTACTS_PER_DAY} a day is our reading, for the lender to set.", "cite": "RBC Directions 2025 para 100 (internal threshold)"})
    return {"allowed": not v, "violations": v, "local_time": local.isoformat(timespec="minutes")}


def agent_status(a: dict, on: date) -> tuple[bool, list[str]]:
    """An agent may be used only with due diligence, verified antecedents, training and a current empanelment (RBC 94-96; HFC 170(2), (3), (4))."""
    problems = []
    if not (a.get("empanelled_from") and a.get("empanelled_to") and a["empanelled_from"] <= on.isoformat() <= a["empanelled_to"]):
        problems.append("empanelment period not current")
    if not a.get("authorisation_ref"):
        problems.append("no notice and authorisation letter on record")
    if not a.get("police_verification_date"):
        problems.append("antecedents (police verification) not verified")
    if not a.get("iibf_certificate"):
        problems.append("no IIBF training certificate")
    return (not problems, problems)
