import copy
import pytest

from griha.audit import AuditLog
from griha.engine import Engine, digest
from griha.fraud import balance_breaks
from griha.synth import make_case


@pytest.fixture(scope="module")
def engine():
    return Engine()


def honest(seed):
    return make_case(seed)[0]


def test_decision_is_deterministic_and_replayable(engine):
    app = honest(4242)
    d1 = engine.underwrite(app, record=True)
    d2 = engine.underwrite(app, graph_flags=engine.audit.entries[-1]["payload"]["graph_flags"], record=False)
    assert digest(d1) == digest(d2)
    assert engine.replay(engine.audit.entries[-1])["match"] is True


def test_audit_chain_detects_tampering(engine):
    for s in range(5):
        engine.underwrite(honest(5000 + s), record=True)
    assert engine.audit.verify()["ok"]
    from griha.audit import verify_entries
    forged = copy.deepcopy(engine.audit.entries)
    forged[2]["payload"]["outcome"] = "APPROVE" if forged[2]["payload"]["outcome"] != "APPROVE" else "REJECT"
    res = verify_entries(forged)
    assert not res["ok"] and res["broken_at"] == 2


def test_sanctions_hit_goes_to_compliance_officer_not_auto_declined(engine):
    app = honest(7001)
    app.kyc.sanctions_hit = True
    d = engine.underwrite(app, record=False)
    assert d.outcome == "REFER" and d.refer_queue == "FRAUD" and any(r.code == "AML_SANCTIONS" for r in d.reasons)


def test_missing_bureau_refers_to_data_queue(engine):
    app = honest(7002)
    app.bureau = None
    d = engine.underwrite(app, record=False)
    assert d.outcome == "REFER" and d.refer_queue == "DATA"


def test_edited_statement_is_flagged_as_fraud(engine):
    app, truth = make_case(8001, fraud="edit")
    assert balance_breaks(app.statement) >= 2
    d = engine.underwrite(app, record=False)
    assert d.outcome != "APPROVE" and any(f["code"] == "BALANCE_BREAK" for f in d.fraud["flags"])


def test_honest_statement_has_consistent_balances():
    for s in range(20):
        assert balance_breaks(honest(9000 + s).statement) == 0


def test_risk_is_monotone_in_foir(engine):
    app = honest(7100)
    from griha import features, income
    inc = income.analyse(app.statement, app.applicant.employment, None, None)
    prop = engine.valuer.assess(app.property)
    pds = []
    for amt in (1_000_000, 1_500_000, 2_000_000, 3_000_000):
        f = features.build(app, inc, prop["assessed_value"], amt, 240)
        pds.append(engine.risk.predict(f)["pd"])
    assert pds == sorted(pds)


def test_offer_respects_affordability_and_has_kfs(engine):
    approved = 0
    for s in range(60):
        app = honest(11000 + s)
        d = engine.underwrite(app, record=False)
        if d.outcome == "APPROVE":
            approved += 1
            assert d.offer["amount"] <= app.loan.amount
            assert d.kfs["apr_pct"] >= d.kfs["interest_rate_pct" if False else "interest_rate_annual_pct"]
            assert d.policy_hash and d.model_version
    assert approved > 10


def test_risk_ordering_on_population(engine):
    import statistics
    ap, allv = [], []
    for s in range(800):
        app, truth = make_case(20000 + s)
        d = engine.underwrite(app, record=False)
        allv.append(truth["default"])
        if d.outcome == "APPROVE":
            ap.append(truth["default"])
    assert statistics.fmean(ap) < 0.75 * statistics.fmean(allv)


def test_new_evidence_stages_present(engine):
    d = engine.underwrite(honest(31337), record=False)
    stages = {e.stage: e for e in d.evidence}
    assert {"data_integration", "compliance"} <= set(stages)
    ds = stages["data_integration"].data
    assert len(ds["sources"]) == 4 and {x["id"] for x in ds["documents"]} >= {"pan", "aadhaar", "statement", "title"}
    controls = {c["id"]: c for c in stages["compliance"].data["controls"]}
    assert controls["FAIR"]["status"] == "met" and controls["AUDIT"]["status"] == "met" and "LTV" in controls
    if d.pd:
        assert 300 <= d.pd["score"] <= 900 and d.pd["band"] in "ABCDE"
    assert "aml" in d.fraud


def test_outage_routes_to_data_queue_and_cash_rules():
    from griha.compliance import evaluate  # noqa: F401
    from fastapi.testclient import TestClient
    from griha.api import app as api
    with TestClient(api) as c:
        ref = c.get("/api/reference").json()
        pin = next(x for x in ref["cities"] if x["name"] == "Jaipur")["pins"][0]
        f = {"name": "Outage Test", "dob": "1988-04-12", "pan": "ABCDE1234F", "phone": "9876543210", "gender": "F", "employment": "salaried",
             "employer": "Metro Hospital", "monthly_income": 62000, "existing_emi": 4000, "city": "Jaipur", "pincode": pin, "product": "HL",
             "amount": 2400000, "tenure_months": 240, "property_type": "apartment", "area_sqft": 950, "property_age_years": 6,
             "declared_value": 3600000, "survey_no": "KH-221/4", "consent": True, "simulate_outage": "bureau"}
        d = c.post("/api/applications/new", json=f).json()["decision"]
        assert d["outcome"] == "REFER" and d["refer_queue"] == "DATA"
        e = c.post("/api/eligibility", json={"product": "HL", "monthly_income": 62000, "existing_emi": 4000, "tenure_years": 20, "property_value": 3600000}).json()
        assert e["eligible"] and e["max_loan"] > 0 and e["binding"] in ("by_income", "by_property", "by_product")
        assert c.post("/api/eligibility", json={"product": "HL", "monthly_income": 10000, "existing_emi": 20000, "tenure_years": 20, "property_value": 3600000}).status_code == 422
        h = {"Authorization": "Bearer " + c.post("/api/login", json={"email": "officer@griha.demo", "password": "griha-demo"}).json()["token"]}
        b = c.get("/api/benchmark?n=40", headers=h).json()
        assert b["p95_ms"] > 0 and b["per_second_one_worker"] > 1
        assert c.get("/api/benchmark").status_code == 401


def test_same_applicant_reapplying_is_not_a_fraud_ring():
    from griha.fraud import EntityGraph
    g = EntityGraph()
    base = honest(4711)
    for i in range(6):
        a = base.model_copy(deep=True)
        a.case_id = f"R{i}"
        flags = g.peek(a)
        assert flags["ring_size"] == 1 and not flags["shared_phone_other_pan"], flags
        g.add(a)


def test_a_real_ring_of_different_applicants_is_still_caught():
    from griha.fraud import EntityGraph
    from griha.synth import make_case, RING_PHONES
    g = EntityGraph()
    for s in range(960_000, 960_030):
        g.add(make_case(s, fraud="ring")[0])
    hits = 0
    for s in range(970_100, 970_140):
        a, _ = make_case(s, fraud="ring")
        f = g.peek(a)
        hits += f["ring_size"] >= 4 and f["shared_phone_other_pan"]
    assert hits >= 20
