"""Data-source lineage and document verification, shown on every case. Sources are SIMULATED adapters shaped like the real
feeds (Account Aggregator, bureau, KYC, land records). Latencies are deterministic per case so runs replay exactly."""
from __future__ import annotations

import hashlib

from .models import ApplicationInput


def _ms(case_id: str, name: str, lo: int, hi: int) -> int:
    h = int(hashlib.sha256(f"{case_id}|{name}".encode()).hexdigest()[:6], 16)
    return lo + h % (hi - lo)


def sources(app: ApplicationInput, failed: set | None = None, fetch: list | None = None) -> list[dict]:
    cid = app.case_id
    failed = failed or set()
    att = {f["source"]: f.get("attempts", 1) for f in (fetch or [])}
    sim = app.statement_source.startswith("simulated")
    out = [
        {"id": "bank", "name": "Bank statement", "channel": app.statement_source, "status": "ok" if app.statement else "failed",
         "latency_ms": _ms(cid, "bank", 180, 520) if sim else None, "records": len(app.statement), "feeds": ["income", "fraud"]},
        {"id": "bureau", "name": "Credit bureau report", "channel": "simulated bureau pull", "status": "ok" if app.bureau else "failed",
         "latency_ms": _ms(cid, "bureau", 120, 380), "records": 1 if app.bureau else 0, "feeds": ["policy", "risk"]},
        {"id": "kyc", "name": "KYC, e-KYC and sanctions screen", "channel": "simulated KYC and watchlist feed", "status": "ok" if app.kyc else "failed",
         "latency_ms": _ms(cid, "kyc", 90, 300), "records": 1 if app.kyc else 0, "feeds": ["policy", "fraud"]},
        {"id": "land", "name": "Land and title records", "channel": "simulated land-records lookup", "status": "ok",
         "latency_ms": _ms(cid, "land", 200, 600), "records": 1, "feeds": ["property", "policy"]},
    ]
    for o in out:
        if o["id"] in failed:
            o["status"] = "failed"
        o["attempts"] = att.get(o["id"], 1)
    return out


def documents(app: ApplicationInput, balance_breaks: int) -> list[dict]:
    k, p = app.kyc, app.property
    docs: list[dict] = []
    if k is None:
        docs.append({"id": "pan", "name": "PAN card", "status": "missing", "detail": "KYC source unavailable", "method": "registry lookup"})
        docs.append({"id": "aadhaar", "name": "Aadhaar e-KYC", "status": "missing", "detail": "KYC source unavailable", "method": "OTP e-KYC"})
    else:
        warn = k.name_match < 0.85
        docs.append({"id": "pan", "name": "PAN card", "status": "failed" if not k.pan_verified else "warning" if warn else "verified",
                     "detail": f"Name match with PAN record {k.name_match:.0%}" if k.pan_verified else "PAN could not be verified", "method": "registry lookup (simulated)"})
        docs.append({"id": "aadhaar", "name": "Aadhaar e-KYC", "status": "verified" if k.aadhaar_verified else "warning",
                     "detail": f"OTP e-KYC, number ending {app.applicant.aadhaar_last4} (full number never stored)" if k.aadhaar_verified else "e-KYC incomplete, re-verification needed",
                     "method": "OTP e-KYC (simulated)"})
    bad = balance_breaks >= 2 or any(i.get("severity") == "high" for i in app.doc_issues)
    docs.append({"id": "statement", "name": "Bank statement", "status": "failed" if bad else "warning" if app.doc_issues or balance_breaks else "verified",
                 "detail": f"{len(app.statement)} transactions, {balance_breaks} balance break(s)" + (f", {len(app.doc_issues)} document issue(s)" if app.doc_issues else ""),
                 "method": app.statement_source})
    docs.append({"id": "income", "name": "Income proof", "status": "verified", "detail": "Income is derived from bank cash flow, so a salary slip or ITR is optional",
                 "method": "cash-flow underwriting"})
    title_bad = p.litigation
    title_warn = p.encumbrance or not p.approved_plan or not p.rera_registered
    issues = [x for x, f in (("litigation", p.litigation), ("encumbrance", p.encumbrance), ("no approved plan", not p.approved_plan), ("not RERA registered", not p.rera_registered)) if f]
    docs.append({"id": "title", "name": "Property title and approvals", "status": "failed" if title_bad else "warning" if title_warn else "verified",
                 "detail": f"Property {p.property_id}: " + (", ".join(issues) if issues else "clear title, approved plan, RERA registered"), "method": "land-records lookup (simulated)"})
    return docs
