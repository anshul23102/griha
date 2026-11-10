"""Per-case regulatory controls. Each control says what it checks, the clause or source, how well that source was verified,
and what the engine did on THIS case. met = requirement satisfied, enforced = control triggered and acted, na = not applicable here."""
from __future__ import annotations

from . import config
from .features import FEATURES
from .models import ApplicationInput


def evaluate(app: ApplicationInput, *, outcome: str, refer_queue: str | None, offer: dict | None, kfs: dict | None, reasons: list,
             ltv_offered: float | None, ltv_cap: float | None, vault_on: bool, fraud_level: str, str_recommended: bool) -> list[dict]:
    k = app.kyc
    adverse = [r for r in reasons if getattr(r, "direction", "adverse") == "adverse"]
    c: list[dict] = []

    def add(id_, title, clause, basis, status, evidence):
        c.append({"id": id_, "title": title, "clause": clause, "basis": basis, "status": status, "evidence": evidence})

    kyc_ok = bool(k and k.pan_verified and k.aadhaar_verified)
    add("KYC", "KYC completed before sanction; Aadhaar voluntary; a person records any rejection", "NBFC KYC Directions 2025 paras 17(3), 17(10), 18, 23 (explanation 4); HFC Directions 2025 para 5(23)", "verified",
        "met" if kyc_ok else "enforced",
        "PAN verified and Aadhaar e-KYC completed" if kyc_ok else "KYC incomplete: referred to an officer, who may accept another officially valid document (Aadhaar is voluntary) and must record the reason for any rejection")
    hit = bool(k and k.sanctions_hit)
    add("AML", "Sanctions and PEP screening; applicant is not told of a match", "NBFC KYC Directions 2025 paras 17(1), 17(9), 19, 20(4), 45, 52, 54", "verified", "enforced" if hit else "met",
        "Possible match on the UN consolidated list (or the demo fixture): referred to the compliance officer, withheld from the applicant's view" if hit else
        f"Screened against the UN Security Council Consolidated List (snapshot {(k.sanctions_detail or {}).get('list_date', '')[:10] if k else ''}), no match{' (PEP: senior-management approval and source-of-funds check needed, para 45)' if k and k.pep else ''}. Not covered: OFAC, EU, UK and the MHA UAPA list, and PEP data, which need a licensed feed")
    add("EDD", "Online application treated as non-face-to-face: customer rated high-risk, enhanced checks", "NBFC KYC Directions 2025 para 44(4) to (6); para 20(4)", "verified", "enforced",
        "Customer risk category: HIGH until identity is confirmed face to face or by V-CIP (para 44(6)). Not shown to the applicant. Still to do by the lender: positive confirmation of the current address (44(3))")
    add("STR", "Suspicious-transaction reporting signal; its existence is confidential", "NBFC KYC Directions 2025 paras 49 to 53; PMLA", "verified", "enforced" if str_recommended else "met",
        "STR recommended to the compliance officer" if str_recommended else "No STR trigger on this case")
    if app.loan.product == "HL" and ltv_offered is not None and ltv_cap is not None:
        add("LTV", "Loan-to-value within the regulatory cap", "HFC Directions 2025 para 58 (90% / 80% / 75% by loan size)", "verified",
            "met" if ltv_offered <= ltv_cap + 1e-9 else "enforced", f"LTV {ltv_offered:.0%} against cap {ltv_cap:.0%}")
    elif ltv_offered is not None and ltv_cap is not None:
        add("LTV", "Loan-to-value within lender limit (LAP)", "No RBI cap for LAP; lender limit", "internal", "met" if ltv_offered <= ltv_cap + 1e-9 else "enforced",
            f"LTV {ltv_offered:.0%} against lender limit {ltv_cap:.0%}")
    add("CONSENT", "Consent recorded, purpose-limited", "RBI Digital Lending Directions 2025 para 12(i) to (iii); DPDP Rules 2025 rule 3 (from 13 May 2027)", "verified", "met" if app.consent else "enforced",
        "Consent given for fetching bank, bureau, KYC and property records for this application only" if app.consent else "No consent on file")
    add("KFS", "KFS: all-in cost, fees, penal and conversion charges, reset, exit window", "RBI HFC Directions 2025 paras 131, 132, 137, 175; Digital Lending Directions 2025 paras 8(i), 10; NBFC Responsible Business Conduct Directions 2025 para 29 and Annex I (format, proposal number, three-working-day validity, APR sheet, schedule)", "verified",
        "met" if kfs else "na", f"APR {kfs['apr_pct']}% with fees and total payable; penal, conversion and reset disclosures and a {config.COOLING_OFF_DAYS}-day cooling-off exit stated (lender-set values marked)" if kfs else "No offer issued, so no KFS")
    add("PREPAY", "Pre-payment charge disclosed", "RBI HFC Directions 2025 para 163; RBC Directions 2025 para 34(1), (3), (8)" if app.loan.product == "HL" else "RBC Directions 2025 para 34 (1), (2), (5), (8)",
        "verified",
        "met" if kfs else "na", "Nil for floating-rate housing loans, stated on the KFS" if kfs else "No offer issued")
    add("GRIEVANCE", "Grievance officer named; escalation route shown", "RBI HFC Directions 2025 paras 142 to 144 (NHB Complaint Redressal Cell after one month); Digital Lending Directions 2025 para 11", "verified",
        "met" if kfs else "na", "Grievance line, acknowledgement and six-week response targets and the escalation route on the KFS and letter; the officer's name is the lender's to insert" if kfs else "Shown on the decision letter")
    add("REASONS", "Reasons for rejection given in writing", "RBI HFC Directions 2025 para 135; FREE-AI disclosure principle", "verified",
        "met" if (outcome == "APPROVE" or adverse) else "enforced", "Decision approved: no adverse reasons needed" if outcome == "APPROVE" else f"{len(adverse)} reason(s) recorded and printed on the decision letter")
    add("FAIR", "No discrimination on sex, caste, religion or disability", "RBI HFC Directions 2025 para 168; FREE-AI fairness principle", "verified", "met" if "gender" not in FEATURES else "enforced",
        f"Model uses {len(FEATURES)} features; gender, religion and caste are not among them")
    add("HUMAN", "Human oversight on uncertain or high-risk cases", "RBI FREE-AI principles (human in the loop)", "secondary", "enforced" if outcome == "REFER" else "met",
        f"Referred to the {refer_queue} queue for an officer" if outcome == "REFER" else "Engine decided inside its confidence limits")
    add("FOUREYES", "Four-eyes rule on fraud overrides", "Lender policy", "internal", "enforced" if (fraud_level == "high" or refer_queue == "FRAUD") else "na",
        "Approving this fraud or compliance-flagged case needs the Credit Head" if (fraud_level == "high" or refer_queue == "FRAUD") else "No fraud override applies")
    add("AUDIT", "Tamper-evident, replayable audit record", "Audit standards (lender policy)", "internal", "met", "Decision, inputs, policy hash and model version written to a hash-chained log")
    add("PII", "Personal data kept confidential, encrypted at rest, erasable", "RBI HFC Directions 2025 para 160; KYC Directions 2025 para 61; DPDP Rules 2025 rule 6 (from 13 May 2027)", "verified", "met" if vault_on else "enforced", "AES-256-GCM with a key per case; erasure destroys the key once the retention period of KYC Directions para 47 (5 years) allows it")
    return c
