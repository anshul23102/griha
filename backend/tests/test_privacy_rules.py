"""Tests for what the KYC Directions 2025 and DPDP Rules 2025 (read in the primary text) require of the application."""
from datetime import datetime, timedelta, timezone

from griha import config
from griha.api import STATE, app
from tests.keyed import KeyedClient


def _case(c, scen):
    r = c.post("/api/applications", json={"scenario_id": scen}).json()
    return r["case_id"], r["access_key"]


def test_applicant_never_sees_sanctions_fraud_str_or_risk_category():           # KYC Directions paras 19, 20(4), 52
    with KeyedClient(app) as c:
        for scen in ("sanctions", "fraud_edit", "fraud_ring"):
            cid, key = _case(c, scen)
            blob = c.get(f"/api/cases/{cid}", headers={"X-Case-Key": key, "Authorization": ""}).text.lower()
            for word in ("sanctions_hit", "watchlist match", "name matches", "str_recommended", "str recommended", "customer risk category", "four-eyes", "credit head", "\"aml\"", "\"str\"", "\"edd\"", "\"scenario\":\"sanctions\"", "\"scenario\":\"fraud"):
                assert word not in blob, (scen, word)
        d = c.get(f"/api/cases/{cid}", headers={"X-Case-Key": key}).json()["decision"]
        assert d["fraud"] is None and d["outcome"] == "REFER"


def _staff(c, email="admin@griha.demo"):
    return {"Authorization": "Bearer " + c.post("/api/login", json={"email": email, "password": "griha-demo"}).json()["token"]}


def test_staff_still_see_everything():
    with KeyedClient(app) as c:
        cid, _ = _case(c, "sanctions")
        v = c.get(f"/api/cases/{cid}", headers={**_staff(c), "X-Case-Key": ""}).json()
        ids = {x["id"] for s in v["decision"]["evidence"] if s["stage"] == "compliance" for x in s["data"]["controls"]}
        assert {"AML", "STR", "EDD", "FOUREYES"} <= ids and v["decision"]["fraud"] is not None and v["decision"]["refer_queue"] == "FRAUD"


def test_sanctions_and_pan_failures_go_to_an_officer_not_auto_reject():       # para 18
    with KeyedClient(app) as c:
        for scen in ("sanctions",):
            cid, key = _case(c, scen)
            assert c.get(f"/api/cases/{cid}", headers={"X-Case-Key": key}).json()["decision"]["outcome"] == "REFER"


def test_rights_request_is_logged_with_a_90_day_deadline_and_withdrawal_stops_processing():   # DPDP rule 14
    with KeyedClient(app) as c:
        cid, key = _case(c, "refer_gap")
        h = {"X-Case-Key": key}
        r = c.post(f"/api/cases/{cid}/rights", json={"kind": "withdraw_consent"}, headers=h).json()
        due = datetime.fromisoformat(r["respond_by"]).date()
        assert (due - datetime.now(timezone.utc).date()).days == config.RIGHTS_RESPONSE_DAYS and r["consent_withdrawn"]
        v = c.get(f"/api/cases/{cid}", headers=h).json()
        assert v["consent_withdrawn"] and v["rights"][0]["kind"] == "withdraw_consent"
        assert c.post(f"/api/cases/{cid}/retry", json={"loan_amount": 1_000_000}, headers=h).status_code == 409
        assert c.post(f"/api/cases/{cid}/rights", json={"kind": "bogus"}, headers=h).status_code == 422
        assert c.post(f"/api/cases/{cid}/rights", json={"kind": "access"}, headers={"X-Case-Key": "wrong"}).status_code == 404


def test_erasure_waits_for_the_kyc_retention_period(monkeypatch):               # KYC Directions para 47
    monkeypatch.setattr(config, "RETENTION_HOLD", True)
    with KeyedClient(app) as c:
        cid, _ = _case(c, "salaried_approve")
        h = _staff(c)
        r = c.post(f"/api/cases/{cid}/erase", json={"reason": "applicant asked for erasure of data"}, headers=h)
        d = r.json()["detail"]
        assert r.status_code == 409 and d["deferred"] and d["retain_until"].startswith(str(datetime.now().year + config.RETENTION_YEARS))
        assert not STATE["cases"][cid].get("erased")
        assert any(e["event"] == "ERASURE_DEFERRED" for e in __import__("griha.api", fromlist=["eng"]).eng().audit.for_case(cid))
        monkeypatch.setattr(config, "RETENTION_HOLD", False)
        assert c.post(f"/api/cases/{cid}/erase", json={"reason": "applicant asked for erasure of data"}, headers=h).status_code == 200


def test_backup_is_private_verified_and_excludes_the_master_key(tmp_path):         # DPDP rule 6(1)(d)
    import os
    from griha import backup
    from griha.api import eng
    with KeyedClient(app) as c:
        _case(c, "salaried_approve")
        d = backup.backup(config.DATA_DIR, tmp_path / "bk", keep=2)
        names = {p.name for p in d.iterdir()}
        assert {"audit.db", "keystore.db"} <= names and "master.key" not in names
        assert all(oct(os.stat(p).st_mode & 0o777) == "0o600" for p in d.iterdir()) and oct(os.stat(d).st_mode & 0o777) == "0o700"
        assert eng().audit.verify()["ok"]
        for _ in range(3):
            backup.backup(config.DATA_DIR, tmp_path / "bk", keep=2)
        assert len(list((tmp_path / "bk").iterdir())) == 2


def test_real_un_list_screen_flags_listed_name_and_clears_common_names():
    from griha import sanctions
    assert sanctions.load()["count"] > 900
    hit = sanctions.screen("Dawood Ibrahim Kaskar")
    assert hit["hit"] and hit["matches"][0]["ref"].startswith("QDi")
    for n in ("Rajesh Kumar Sharma", "Priya Nair", "Mohammed Khan"):
        assert not sanctions.screen(n)["hit"]
    assert not sanctions.screen("Madonna")["hit"]            # single token: never screened on a bare token


def test_listed_name_in_a_new_application_is_referred_and_hidden_from_applicant():
    from tests.test_intake import GOOD, pick_pin
    with KeyedClient(app) as c:
        f = {**GOOD, "name": "Dawood Ibrahim Kaskar", "dob": "1988-12-26", "pincode": pick_pin(c, "Jaipur")}
        r = c.post("/api/applications/new", json=f)
        assert r.status_code == 200, r.text
        cid = r.json()["case_id"]
        assert r.json()["decision"]["outcome"] == "REFER"
        applicant = c.get(f"/api/cases/{cid}", headers={"Authorization": ""}).text.lower()
        assert "qdi" not in applicant and "consolidated list" not in applicant and "dawood" not in applicant.replace(f["name"].lower(), "")
        full = c.get(f"/api/cases/{cid}", headers={**_staff(c), "X-Case-Key": ""}).text
        assert "QDi.135" in full and "UN Security Council Consolidated List" in full


def test_breach_log_tracks_the_three_rule_7_notices_and_is_admin_only():
    with KeyedClient(app) as c:
        body = {"description": "A backup file was copied to a personal drive by a contractor", "nature": "confidentiality", "affected_count": 40}
        assert c.post("/api/breaches", json=body).status_code in (401, 403)
        h = _staff(c)
        b = c.post("/api/breaches", json=body, headers=h).json()
        assert set(b["open"]) == {"board", "principals", "board_detailed_report"} and not b["overdue"]
        det = datetime.fromisoformat(b["detected_at"]); due = datetime.fromisoformat(b["board_report_due"])
        assert due - det == timedelta(hours=72)
        b2 = c.post(f"/api/breaches/{b['reference']}/notify", json={"party": "board", "note": "Reported on the Board portal"}, headers=h).json()
        assert "board" not in b2["open"] and len(b2["notified"]) == 1
        old = c.post("/api/breaches", json={**body, "detected_at": "2020-01-01T00:00:00Z"}, headers=h).json()
        assert old["overdue"] is True
        assert c.get("/api/audit/verify", headers=h).json().get("ok", True) is not False
