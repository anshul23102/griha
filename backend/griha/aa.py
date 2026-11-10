"""Account Aggregator adapter: reads bank data in the ReBIT DEPOSIT FI-type format (the format an FIP returns through an Account Aggregator).

Format source: the public ReBIT specification, https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html
(namespace http://api.rebit.org.in/FISchema/deposit; Account > Profile > Holders > Holder, Summary, Transactions > Transaction).
We read the structure from the published documentation. What we do NOT do: the consent artefact, the FIU-to-AA signed requests and the
encrypted FI payload exchange. This adapter is the data-format layer only; it takes the decrypted FI document. Both the XML form and
the JSON form with the same names are accepted.

The result is the same Extraction object the PDF path produces, so every downstream check (balance continuity, holder match, cash-flow
income, fraud signals, audit) works unchanged. Input is untrusted: DTDs are rejected, sizes capped, narrations sanitised.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from xml.etree import ElementTree as ET  # nosec B405: used only to build XML and for ParseError; all parsing goes through defusedxml

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from .docextract import INJECTION_RX, Extraction, Issue, UploadError
from .models import Txn

MAX_BYTES = 4 * 1024 * 1024
MAX_TXNS = 20000
MODES = {"CASH", "ATM", "CARD", "UPI", "FT", "OTHERS"}
FORMAT_NAME = "ReBIT DEPOSIT FI schema"
SCHEMA_URL = "https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html"
_CTRL = re.compile(r"[\x00-\x1f\x7f\u202a-\u202e\u2066-\u2069]")


def _xml_to_dict(el: ET.Element) -> dict:
    """Attributes and child elements become one dict; repeated children become lists. Namespaces are dropped."""
    d: dict = {k.split("}")[-1]: v for k, v in el.attrib.items()}
    for ch in el:
        tag = ch.tag.split("}")[-1]
        v = _xml_to_dict(ch)
        if tag in d:
            d[tag] = d[tag] if isinstance(d[tag], list) else [d[tag]]
            d[tag].append(v)
        else:
            d[tag] = v
    return d


def _lc(o):
    """Lower-case every key so 'Transactions' and 'transactions' read the same."""
    if isinstance(o, dict):
        return {str(k).lower(): _lc(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_lc(x) for x in o]
    return o


def _many(x) -> list:
    return x if isinstance(x, list) else ([] if x is None else [x])


def load(data: bytes) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise UploadError(f"The file is empty or larger than {MAX_BYTES // (1024 * 1024)} MB")
    head = data.lstrip()[:1]
    try:
        if head == b"{":
            doc = json.loads(data.decode("utf-8"))
            if isinstance(doc, dict) and len(doc) == 1 and isinstance(next(iter(doc.values())), dict) and "account" in {k.lower() for k in doc}:
                doc = next(iter(doc.values()))
        elif head == b"<":
            low = data[:4096].lower()
            if b"<!doctype" in low or b"<!entity" in low or b"<!entity" in data.lower():
                raise UploadError("XML with a DTD or entities is rejected")
            root = SafeET.fromstring(data)
            doc = _xml_to_dict(root)
            if root.tag.split("}")[-1].lower() != "account":
                raise UploadError("The root element must be Account")
        else:
            raise UploadError("Unrecognised file: expected JSON or XML")
    except UploadError:
        raise
    except (ValueError, ET.ParseError, DefusedXmlException, UnicodeDecodeError):
        raise UploadError("The file is not valid JSON or XML")
    if not isinstance(doc, dict):
        raise UploadError("The document must be an Account object")
    return _lc(doc)


def _num(v, what: str) -> float:
    try:
        x = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        raise UploadError(f"{what} is not a number")
    if x != x or x in (float("inf"), float("-inf")):
        raise UploadError(f"{what} is not a finite number")
    return x


def _ts(v, what: str) -> datetime:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        raise UploadError(f"{what} is not an ISO 8601 date-time")


def parse_fi(data: bytes, *, applicant_name: str | None = None) -> Extraction:
    acc = load(data)
    if str(acc.get("type", "")).lower() != "deposit":
        raise UploadError("Only the DEPOSIT FI type is supported (Account type must be 'deposit')")
    for req in ("maskedaccnumber", "linkedaccref", "version"):
        if req not in acc:
            raise UploadError(f"Mandatory Account attribute missing: {req}")
    ver = _num(acc["version"], "Account version")
    if not 0 <= ver <= 2.0:
        raise UploadError("Account version must be between 0.0 and 2.0")
    holders = _many(((acc.get("profile") or {}).get("holders") or {}).get("holder"))
    if not holders:
        raise UploadError("Profile/Holders/Holder is required")
    txs = acc.get("transactions") or {}
    rows = _many(txs.get("transaction"))
    if not rows:
        raise UploadError("No transactions in the document")
    if len(rows) > MAX_TXNS:
        raise UploadError(f"More than {MAX_TXNS} transactions")

    issues: list[Issue] = []
    parsed: list[tuple[datetime, float, float, str, str]] = []
    seen: set[str] = set()
    dupes = 0
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            raise UploadError(f"Transaction {i} is malformed")
        for req in ("type", "mode", "amount", "currentbalance", "transactiontimestamp", "txnid"):
            if req not in r:
                raise UploadError(f"Transaction {i}: mandatory attribute missing: {req}")
        t = str(r["type"]).upper()
        if t not in ("CREDIT", "DEBIT"):
            raise UploadError(f"Transaction {i}: type must be CREDIT or DEBIT")
        mode = str(r["mode"]).upper()
        if mode not in MODES:
            raise UploadError(f"Transaction {i}: mode '{str(r['mode'])[:12]}' is not one of {sorted(MODES)}")
        amt = _num(r["amount"], f"Transaction {i} amount")
        if amt < 0:
            raise UploadError(f"Transaction {i}: amount must not be negative (the sign is carried by type)")
        bal = _num(r["currentbalance"], f"Transaction {i} balance")
        ts = _ts(r["transactiontimestamp"], f"Transaction {i} timestamp")
        tid = str(r["txnid"])[:64]
        if tid in seen:
            dupes += 1
            continue
        seen.add(tid)
        narr = _CTRL.sub(" ", str(r.get("narration", "")))[:200].strip()
        parsed.append((ts.replace(tzinfo=None), amt if t == "CREDIT" else -amt, bal, narr or mode, tid))
    if dupes:
        issues.append(Issue(code="DUPLICATE_TXN", severity="warn", weight=0.2, text=f"{dupes} repeated transaction id(s) were ignored"))
    parsed.sort(key=lambda p: p[0])
    txns = [Txn(d=p[0].date(), amount=round(p[1], 2), balance=round(p[2], 2), narration=p[3]) for p in parsed]

    opening = round(parsed[0][2] - parsed[0][1], 2)
    closing = round(parsed[-1][2], 2)
    summ = acc.get("summary") or {}
    if "currentbalance" in summ:
        stated = _num(summ["currentbalance"], "Summary currentBalance")
        if abs(stated - closing) > 1.0:
            issues.append(Issue(code="TOTAL_MISMATCH", severity="high", weight=0.5,
                                text=f"Summary balance {stated:,.2f} differs from the last transaction balance {closing:,.2f}"))
    if str(summ.get("status", "ACTIVE")).upper() == "INACTIVE":
        issues.append(Issue(code="ACCOUNT_INACTIVE", severity="warn", weight=0.3, text="The account is marked INACTIVE in the Summary"))
    start, end = txs.get("startdate"), txs.get("enddate")
    holder_name = str(holders[0].get("name", "")).strip() or None if isinstance(holders[0], dict) else None
    if applicant_name and holder_name and re.sub(r"[^a-z]", "", applicant_name.lower()) != re.sub(r"[^a-z]", "", holder_name.lower()):
        issues.append(Issue(code="HOLDER_MISMATCH", severity="high", weight=0.5,
                            text=f"Account holder is '{holder_name}', the applicant is '{applicant_name}'"))
    hits = sorted({m.group(0).lower() for t in txns for m in [INJECTION_RX.search(t.narration)] if m})
    if hits:
        issues.append(Issue(code="PROMPT_INJECTION", severity="high", weight=0.7,
                            text="Narration contains text addressed to an AI reviewer (" + ", ".join(hits[:3]) + "). It was treated as data and ignored."))
    return Extraction(method="account_aggregator", provider="rebit_deposit", model=None, fallback_reason=None, holder_name=holder_name,
                      period_from=str(start) if start else txns[0].d.isoformat(), period_to=str(end) if end else txns[-1].d.isoformat(),
                      opening_balance=opening, closing_balance=closing, pages=0, txns=txns, issues=issues)


def to_fi(app, *, as_xml: bool = False) -> bytes:
    """Build a DEPOSIT document from a synthetic application (for the demo download and for round-trip tests). Synthetic data, shaped like the spec."""
    a = app
    acct = {"type": "deposit", "maskedAccNumber": "XXXXXX" + a.applicant.phone[-4:], "version": "1.2", "linkedAccRef": "SYN-" + a.case_id}
    first, last = a.statement[0], a.statement[-1]
    holder = {"name": a.applicant.name, "dob": a.applicant.dob.isoformat(), "mobile": a.applicant.phone, "nominee": "REGISTERED",
              "email": "applicant@example.invalid", "pan": a.applicant.pan, "ckycCompliance": "true"}
    summary = {"currentBalance": f"{last.balance:.2f}", "balanceDateTime": f"{last.d.isoformat()}T23:59:59", "type": "SAVINGS", "branch": "SYNTHETIC",
               "facility": "OD", "ifscCode": "SYNT0000000", "micrCode": "000000000", "openingDate": "2015-01-01", "currentODLimit": "0",
               "drawingLimit": "0", "status": "ACTIVE"}
    tx = [{"type": "CREDIT" if t.amount >= 0 else "DEBIT", "mode": "UPI" if "UPI" in t.narration.upper() else "FT", "amount": f"{abs(t.amount):.2f}",
           "currentBalance": f"{t.balance:.2f}", "transactionTimestamp": f"{t.d.isoformat()}T10:{i % 60:02d}:00", "valueDate": t.d.isoformat(),
           "txnId": f"T{i:06d}", "narration": t.narration, "reference": f"R{i:06d}"} for i, t in enumerate(a.statement)]
    transactions = {"startDate": first.d.isoformat(), "endDate": last.d.isoformat(), "transaction": tx}
    if not as_xml:
        return json.dumps({**acct, "profile": {"holders": {"type": "SINGLE", "holder": [holder]}}, "summary": summary, "transactions": transactions}, indent=1).encode()
    ns = "http://api.rebit.org.in/FISchema/deposit"
    root = ET.Element(f"{{{ns}}}Account", acct)
    ET.register_namespace("aa", ns)
    hs = ET.SubElement(ET.SubElement(ET.SubElement(root, f"{{{ns}}}Profile"), f"{{{ns}}}Holders"), f"{{{ns}}}Holder", holder)
    root.find(f"{{{ns}}}Profile/{{{ns}}}Holders").set("type", "SINGLE")
    ET.SubElement(root, f"{{{ns}}}Summary", summary)
    ts = ET.SubElement(root, f"{{{ns}}}Transactions", {"startDate": transactions["startDate"], "endDate": transactions["endDate"]})
    for t in tx:
        ET.SubElement(ts, f"{{{ns}}}Transaction", t)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
