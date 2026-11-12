"""Access control and credential hardening. These run against the real API."""
import pytest
from fastapi.testclient import TestClient

from griha import auth
from griha.api import app


@pytest.fixture(scope="module")
def plain():
    with TestClient(app) as c:
        yield c


def _login(c, email="officer@griha.demo", pw="griha-demo"):
    return c.post("/api/login", json={"email": email, "password": pw})


def test_case_is_private_without_its_key(plain):
    c = plain.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    cid, key = c["case_id"], c["access_key"]
    assert len(key) == 32
    for path in ("", "/progress"):
        assert plain.get(f"/api/cases/{cid}{path}").status_code == 404                      # no key
        assert plain.get(f"/api/cases/{cid}{path}", headers={"X-Case-Key": "0" * 32}).status_code == 404   # wrong key
    assert plain.post(f"/api/cases/{cid}/path-to-yes").status_code == 404
    assert plain.post(f"/api/cases/{cid}/retry", json={}).status_code == 404
    assert plain.get(f"/api/cases/{cid}", headers={"X-Case-Key": key}).status_code == 200
    # a key for one case never opens another
    other = plain.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    assert plain.get(f"/api/cases/{other['case_id']}", headers={"X-Case-Key": key}).status_code == 404


def test_unknown_and_private_cases_look_identical(plain):
    r1 = plain.get("/api/cases/A-DOESNOTEXIST")
    c = plain.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    r2 = plain.get(f"/api/cases/{c['case_id']}")
    assert r1.status_code == r2.status_code == 404 and r1.json() == r2.json()


def test_staff_can_open_any_case_and_public_stats_carry_no_ids(plain):
    c = plain.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    tok = _login(plain).json()["token"]
    assert plain.get(f"/api/cases/{c['case_id']}", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    s = plain.get("/api/stats").json()
    assert all("case_id" not in r for r in s["recent"])
    assert c["case_id"] not in plain.get("/api/stats").text


def test_case_key_is_stable_and_secret_dependent():
    assert auth.case_key("A-1") == auth.case_key("A-1") != auth.case_key("A-2")


def test_logout_revokes_token(plain):
    tok = _login(plain).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert plain.get("/api/cases", headers=h).status_code == 200
    assert plain.post("/api/logout", headers=h).status_code == 200
    assert plain.get("/api/cases", headers=h).status_code == 401


def test_salts_differ_and_account_locks_after_repeated_failures(plain):
    assert auth.USERS["officer@griha.demo"]["pw"] != auth.USERS["admin@griha.demo"]["pw"]     # same password, different salts
    for _ in range(auth.LOCKOUT_AFTER):
        assert _login(plain, "admin@griha.demo", "wrong").status_code == 401
    assert _login(plain, "admin@griha.demo", "wrong").status_code == 429
    assert _login(plain, "admin@griha.demo").status_code == 429          # even the right password is refused while locked
    auth._FAILS.clear()


def test_metrics_and_health_are_not_rate_limited(plain):
    assert all(plain.get("/api/health").status_code == 200 for _ in range(3))


def test_security_headers_and_no_wildcard_cors(plain):
    r = plain.get("/api/health", headers={"Origin": "https://evil.example"})
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert r.headers.get("access-control-allow-origin") in (None, "http://localhost:5173")


GOOD = {"name": "Test Person", "dob": "1990-01-01", "pan": "ABCDE1234F", "phone": "9876543210", "gender": "F", "employment": "salaried", "employer": "Acme",
        "monthly_income": 80000, "city": "Pune", "pincode": "200000", "product": "HL", "amount": 2000000, "tenure_months": 120, "property_type": "apartment",
        "area_sqft": 900, "property_age_years": 3, "declared_value": 3000000, "survey_no": "S-123", "consent": True}


def test_hostile_text_is_refused_and_errors_never_echo_input(plain):
    ok = plain.post("/api/applications/new?wait=true", json=GOOD)
    assert ok.status_code == 200
    for bad in ("a\x00b", "‮evil", "<script>alert(1)</script>"):
        r = plain.post("/api/applications/new?wait=true", json={**GOOD, "name": bad})
        assert r.status_code == 422 and bad not in r.text and "input" not in r.text
    # Infinity used to crash the error serializer with a 500
    r = plain.post("/api/applications/new", content=str(GOOD).replace("'", '"').replace("True", "true").replace("80000", "1e999"),
                   headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_uploaded_document_ids_are_unguessable():
    import re
    from griha.intake import IntakeForm
    pat = IntakeForm.model_fields["document_id"].metadata[0].pattern
    assert re.match(pat, "D-" + "A" * 32) and not re.match(pat, "D-" + "A" * 8)


def test_oversized_body_is_refused_and_vcip_permissions_allowed(plain):
    r = plain.post("/api/applications/new", content=b"x" * (13 * 1024 * 1024), headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    h = plain.get("/api/health").headers["permissions-policy"]
    assert "camera=(self)" in h and "geolocation=(self)" in h and "microphone=()" in h        # V-CIP needs the camera and location on our own origin only
    assert plain.head("/api/health").status_code == 200                                        # uptime monitors send HEAD
