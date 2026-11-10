import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from tests.keyed import KeyedClient

from griha.api import app

GOOD = {"name": "Meena Patel", "dob": "1988-04-12", "pan": "abcde1234f", "phone": "98765 43210", "gender": "F", "employment": "salaried",
        "employer": "Metro Hospital", "monthly_income": 62000, "existing_emi": 4000, "city": "Jaipur", "pincode": "300000",
        "product": "HL", "amount": 2400000, "tenure_months": 240, "property_type": "apartment", "area_sqft": 950,
        "property_age_years": 6, "declared_value": 3600000, "survey_no": "KH-221/4", "consent": True}


@pytest.fixture(scope="module")
def c():
    with KeyedClient(app) as cl:
        yield cl


def pick_pin(c, city):
    ref = c.get("/api/reference").json()
    return next(x for x in ref["cities"] if x["name"] == city)["pins"][0]


def test_reference_is_backend_driven(c):
    r = c.get("/api/reference").json()
    assert any(x["name"] == "Jaipur" and x["pins"] for x in r["cities"]) and r["products"]["HL"]["ltv_caps"]


def test_real_form_produces_a_decision_and_is_deterministic(c):
    f = {**GOOD, "pincode": pick_pin(c, "Jaipur")}
    a = c.post("/api/applications/new", json=f)
    assert a.status_code == 200, a.text
    d1 = a.json()["decision"]
    assert d1["outcome"] in ("APPROVE", "REFER", "REJECT") and a.json()["statement_source"].startswith("simulated")
    d2 = c.post("/api/applications/new", json=f).json()["decision"]
    assert d1["outcome"] == d2["outcome"] and d1["pd"] == d2["pd"]
    assert "XXXX" in a.json()["applicant"]["pan"]


@pytest.mark.parametrize("patch,field", [({"pan": "12345"}, "pan"), ({"phone": "12345"}, "phone"), ({"dob": "2012-01-01"}, "dob"),
                                         ({"consent": False}, "consent"), ({"existing_emi": 99999999}, "existing_emi"), ({"city": "Atlantis"}, "city")])
def test_validation_errors(c, patch, field):
    f = {**GOOD, "pincode": pick_pin(c, "Jaipur"), **patch}
    r = c.post("/api/applications/new", json=f)
    assert r.status_code == 422


def test_watchlist_fixture_refers_and_applicant_is_not_told(c):
    f = {**GOOD, "pincode": pick_pin(c, "Jaipur"), "name": "Vikram Sanctioned"}
    d = c.post("/api/applications/new", json=f).json()["decision"]
    assert d["outcome"] == "REFER" and not any(r["code"] == "AML_SANCTIONS" for r in d["reasons"])
    blob = str(d).lower()
    assert "sanctions_hit" not in blob and "watchlist match" not in blob and "aml_sanctions" not in blob and "str_recommended" not in blob and d["fraud"] is None


def test_audit_has_no_plain_pii_for_new_cases(c):
    f = {**GOOD, "pincode": pick_pin(c, "Jaipur"), "name": "Zubin Qureshi", "pan": "QWERT9876Z"}
    c.post("/api/applications/new", json=f)
    from griha.api import STATE
    raw = json.dumps(STATE["engine"].audit.entries)
    assert "QWERT9876Z" not in raw and "Zubin" not in raw


def test_stats_and_uploaded_source(c):
    s = c.get("/api/stats").json()
    assert s["cases"] >= 1 and s["engine_ms_median"] is not None


def test_retry_works_for_custom_cases(c):
    f = {**GOOD, "pincode": pick_pin(c, "Jaipur"), "amount": 5_000_000, "name": "Retry Case"}
    first = c.post("/api/applications/new", json=f).json()
    path = c.post(f"/api/cases/{first['case_id']}/path-to-yes").json()
    if first["decision"]["outcome"] != "APPROVE" and path and path[0].get("actionable"):
        again = c.post(f"/api/cases/{first['case_id']}/retry", json=path[0]["change"]).json()
        assert again["case_id"] != first["case_id"] and again["decision"]["outcome"] == "APPROVE"
    r = c.post(f"/api/cases/{first['case_id']}/retry", json={"loan_amount": 2_000_000}).json()
    assert r["loan"]["amount"] == 2_000_000
    assert c.post("/api/cases/NOPE/retry", json={}).status_code == 404


def test_stats_recent_has_no_personal_data(c):
    s = c.get("/api/stats").json()
    assert s["recent"] and set(s["recent"][0]) == {"product", "amount", "outcome", "queue", "ms"}
