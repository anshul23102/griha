"""What the applicant may see. The case link gives the applicant their own case, but some of what the engine knows must not reach them:

- NBFC KYC Directions 2025 para 20(4): the risk categorisation of a customer and the reasons for it are kept confidential, to avoid tipping off.
- para 19: where money-laundering or terrorist-financing suspicion exists, the customer is not told.
- para 52: the fact that a suspicious-transaction report was considered or filed is confidential.
Fraud findings, sanctions and watchlist matches, STR signals, the customer risk category and officers' internal notes are therefore removed from the
applicant's view. Staff see the full case. The rejection reasons that HFC Directions para 135 requires are the credit and policy reasons, which stay.
"""
from __future__ import annotations

import copy

HIDDEN_CONTROLS = {"AML", "STR", "FOUREYES", "EDD"}
HIDDEN_RULES = {"AML_SANCTIONS"}
NEUTRAL_HEADLINE = "Your application needs one more check by an officer. We will contact you on your registered number."
NEUTRAL_PTY = "This outcome does not depend on the loan terms. An officer will contact you."


def applicant_decision(d: dict) -> dict:
    d = copy.deepcopy(d)
    hidden = {r["code"] for r in d.get("reasons", []) if r.get("kind") == "fraud" or r.get("code") in HIDDEN_RULES}
    d["reasons"] = [r for r in d.get("reasons", []) if r["code"] not in hidden]
    internal = bool(hidden) or d.get("refer_queue") == "FRAUD"
    d["fraud"] = None
    d["withheld"] = False
    if d.get("outcome") == "REFER" and internal:
        d["headline"], d["refer_queue"], d["withheld"] = NEUTRAL_HEADLINE, "DATA", True
    ev = []
    for s in d.get("evidence", []):
        if s["stage"] == "fraud":
            continue
        if s["stage"] == "policy":
            rules = [r for r in s["data"].get("rules", []) if r["id"] not in HIDDEN_RULES]
            s["data"] = {"rules": rules, "metrics": {k: v for k, v in s["data"].get("metrics", {}).items() if k != "sanctions_hit"}}
            s["status"] = "fail" if any(r["outcome"] == "reject" for r in rules) else "warn" if any(r["outcome"] == "refer" for r in rules) else "ok"
            s["summary"] = f"{sum(r['outcome'] == 'pass' for r in rules)}/{len(rules)} rules passed"
        elif s["stage"] == "compliance":
            ctl = [c for c in s["data"].get("controls", []) if c["id"] not in HIDDEN_CONTROLS]
            s["data"] = {"controls": ctl}
            s["summary"] = f"{sum(c['status'] == 'met' for c in ctl)} met, {sum(c['status'] == 'enforced' for c in ctl)} enforced, {sum(c['status'] == 'na' for c in ctl)} not applicable"
        ev.append(s)
    d["evidence"] = ev
    return d


def applicant_view(v: dict) -> dict:
    if v.get("erased"):
        return v
    v = dict(v)
    v["scenario"] = None            # a prepared-case name such as "sanctions" would give the finding away
    v["decision"] = applicant_decision(v["decision"])
    v["reviews"] = [{"action": r.get("action"), "ts": r.get("ts"), "hash": r.get("hash")} for r in v.get("reviews", [])]   # officers' notes stay internal
    return v
