"""Curated demo scenarios found by scanning the synthetic world (all data synthetic)."""
from __future__ import annotations

from .models import ApplicationInput
from .synth import make_case

SPECS = [
    ("salaried_approve", "Salaried, clean profile", "Stable salary, good bureau history. Expect an instant approval with a Key Fact Statement.", "APPROVE"),
    ("selfemp_approve", "Self-employed, UPI-heavy income", "No salary slip: income is derived from 12 months of bank credits. Expect approval.", "APPROVE"),
    ("counter_offer", "Asked for too much", "Requested amount exceeds what income supports. Expect a reduced counter-offer, not a flat no.", "APPROVE"),
    ("refer_gap", "Borderline: affordability gap", "Large gap between ask and what income supports. Referred, with a Path to Yes.", "REFER"),
    ("reject_dpd", "Recent delinquency", "Severe delinquency in the last 12 months. Declined with clear reasons.", "REJECT"),
    ("property_refer", "Title needs legal review", "Good borrower, but the property has an encumbrance or lacks an approved plan.", "REFER"),
    ("fraud_edit", "Edited bank statement", "Credits were inflated in the PDF. The running balance no longer adds up.", "REFER"),
    ("fraud_dressing", "Window-dressed account", "Large round credits just before applying, with money returned to the same parties.", "REFER"),
    ("fraud_ring", "Linked applications (ring)", "Phone number and property are shared with other applicants.", "REFER"),
    ("sanctions", "Watchlist match", "KYC screening returns a sanctions hit. Referred to the compliance officer; the applicant is not told why.", "REFER"),
]


def _find(engine, pred, start, limit=900):
    for s in range(start, start + limit):
        app, _ = make_case(s)
        d = engine.underwrite(app, record=False, graph_flags={"shared_phone_other_pan": False, "shared_property_other_applicant": False, "ring_size": 1})
        if pred(app, d):
            return app
    raise RuntimeError("scenario not found")


def build(engine) -> dict[str, dict]:
    # seed the entity graph with a ring of prior applications
    for s in range(960_000, 960_030):
        a, _ = make_case(s, fraud="ring")
        engine.graph.add(a)
    out: dict[str, ApplicationInput] = {}
    codes = lambda d: {r.code for r in d.reasons}
    out["salaried_approve"] = _find(engine, lambda a, d: d.outcome == "APPROVE" and a.applicant.employment == "salaried" and not d.offer["reduced"] and a.loan.amount < 4_000_000, 1)
    out["selfemp_approve"] = _find(engine, lambda a, d: d.outcome == "APPROVE" and a.applicant.employment == "self_employed" and not d.offer["reduced"], 1)
    out["counter_offer"] = _find(engine, lambda a, d: d.outcome == "APPROVE" and d.offer["reduced"] and d.offer["amount"] / d.offer["requested"] > 0.7, 1)
    out["refer_gap"] = _find(engine, lambda a, d: d.outcome == "REFER" and "ELIG_GAP" in codes(d) and not d.fraud["flags"], 1)
    out["reject_dpd"] = _find(engine, lambda a, d: d.outcome == "REJECT" and "DPD_12M" in codes(d) and not d.fraud["flags"], 1)
    out["property_refer"] = _find(engine, lambda a, d: d.outcome == "REFER" and d.refer_queue == "PROPERTY" and not d.fraud["flags"], 1)
    out["fraud_edit"] = make_case(970_001, fraud="edit")[0]
    out["fraud_dressing"] = make_case(970_002, fraud="dressing")[0]
    for s in range(970_100, 970_200):
        a, _ = make_case(s, fraud="ring")
        if engine.graph.peek(a)["shared_phone_other_pan"]:
            d = engine.underwrite(a, record=False)
            if d.outcome == "REFER" and d.refer_queue == "FRAUD":
                out["fraud_ring"] = a
                break
    a = _find(engine, lambda a, d: d.outcome == "APPROVE", 5000)
    a.kyc.sanctions_hit = True
    out["sanctions"] = a
    meta = {sid: (title, blurb, expect) for sid, title, blurb, expect in SPECS}
    return {sid: {"id": sid, "title": meta[sid][0], "blurb": meta[sid][1], "expect": meta[sid][2], "app": out[sid]} for sid in meta}
