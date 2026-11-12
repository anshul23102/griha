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


def test_real_lists_screen_listed_names_and_clear_common_ones():
    from griha import sanctions
    d = sanctions.load()
    assert d["count"] > 30000 and set(d["counts"]) == {"UN", "OFAC", "EU", "UK"}
    hit = sanctions.screen("Dawood Ibrahim Kaskar")
    assert hit["hit"] and {m["list"] for m in hit["matches"]} >= {"UN", "OFAC", "EU", "UK"}      # on all four lists, found on all four
    for n in ("Rajesh Kumar Sharma", "Priya Nair", "Meena Patel"):
        assert not sanctions.screen(n)["hit"]
    common = sanctions.screen("Mohammed Khan", 1990)                                              # a real OFAC name, but a different birth year: not a match
    assert common["matches"] and all(m["dob_year_consistent"] is False for m in common["matches"])
    assert not sanctions.screen("Madonna")["hit"]                                                 # a single name part is never screened on its own


def test_listed_name_in_a_new_application_is_referred_and_hidden_from_applicant():
    from tests.test_intake import GOOD, pick_pin
    with KeyedClient(app) as c:
        f = {**GOOD, "name": "Mohammed Masood Azhar Alvi", "dob": "1968-07-10", "tenure_months": 84, "amount": 1500000, "pincode": pick_pin(c, "Jaipur")}
        r = c.post("/api/applications/new", json=f)
        assert r.status_code == 200, r.text
        cid = r.json()["case_id"]
        assert r.json()["decision"]["outcome"] == "REFER"
        applicant = c.get(f"/api/cases/{cid}", headers={"Authorization": ""}).text.lower()
        assert "qdi" not in applicant and "ofac" not in applicant and "consolidated list" not in applicant and "alvi" not in applicant.replace(f["name"].lower(), "")
        full = c.get(f"/api/cases/{cid}", headers={**_staff(c), "X-Case-Key": ""}).text
        assert "QDi.422" in full and "UN, OFAC, EU and UK sanctions lists" in full
        cleared = c.post("/api/applications/new", json={**f, "dob": "1990-01-01", "pan": "ZZZZZ9999Z", "phone": "9000000001", "survey_no": "CLR-1/1"}).json()["decision"]
        assert cleared["outcome"] != "REFER" or cleared["refer_queue"] != "FRAUD"                 # a contradicting birth year clears the name match


# ---- loan servicing: quarterly statement, release of documents, recovery conduct ----
def test_quarterly_statements_follow_the_offers_own_schedule():
    from griha.pricing import build_kfs
    from griha.servicing import quarterly_statements
    from datetime import date
    k = build_kfs(2_000_000, 0.10, 120, "HL", "P-T")
    r = quarterly_statements(k, date(2026, 1, 15), 12)
    assert r["illustrative"] and [s["quarter"] for s in r["statements"]] == [1, 2, 3, 4]
    s4 = r["statements"][-1]
    assert s4["emis_paid"] == 12 and s4["emis_left"] == 108 and s4["emi"] == k["emi"] and s4["apr_pct"] == k["apr_pct"]
    assert s4["period_end"] == "2027-01-15"
    assert abs(s4["principal_recovered"] + s4["outstanding_principal"] - 2_000_000) <= 12          # what is repaid plus what is left is the loan
    assert quarterly_statements(k, date(2026, 1, 15), 2)["statements"] == []                         # no quarter has completed yet


def test_document_release_clock_and_compensation_follow_the_rbc_paragraphs():
    from griha.servicing import Closure, closure_status
    from datetime import date
    on = date(2027, 3, 1)
    assert closure_status(Closure(on), date(2027, 3, 20))["status"] == "within time"
    assert closure_status(Closure(on), date(2027, 3, 31))["release_due_by"] == "2027-03-31"
    late = closure_status(Closure(on), date(2027, 4, 5))                                              # 5 days after the 30-day limit
    assert late["status"] == "overdue" and late["days_late"] == 5 and late["compensation_inr"] == 25_000
    assert closure_status(Closure(on, released_on=date(2027, 3, 30)), date(2027, 6, 1))["compensation_inr"] == 0
    dmg = closure_status(Closure(on, damaged=True), date(2027, 5, 31))                                # lost or damaged: 60 days
    assert dmg["release_due_by"] == "2027-04-30" and dmg["days_late"] == 31 and dmg["compensation_inr"] == 155_000


def test_recovery_contact_rules_cite_their_paragraphs():
    from griha.servicing import check_contact
    from datetime import datetime, timezone
    ok = dict(agent_ok=True, agent_problems=[], target="borrower", recorded_notice=True, sensitive_occasion=False, contacts_today=0, channel="call")
    assert check_contact(at=datetime(2027, 1, 5, 10, 30, tzinfo=timezone.utc), **ok)["allowed"]      # 16:00 IST: inside the window
    r = check_contact(at=datetime(2027, 1, 5, 14, 0, tzinfo=timezone.utc), **ok)                      # 19:30 IST: too late
    assert not r["allowed"] and r["violations"][0]["rule"] == "HOURS" and "para 100" in r["violations"][0]["cite"]
    bad = check_contact(at=datetime(2027, 1, 5, 1, 0, tzinfo=timezone.utc), agent_ok=False, agent_problems=["no IIBF training certificate"], target="relative",
                        recorded_notice=False, sensitive_occasion=True, contacts_today=3, channel="call")
    assert {v["rule"] for v in bad["violations"]} == {"HOURS", "AGENT", "TARGET", "RECORDING", "OCCASION", "PERSISTENT"}
    assert check_contact(at=datetime(2027, 1, 5, 10, 30, tzinfo=timezone.utc), **{**ok, "channel": "letter", "recorded_notice": False})["allowed"]   # a letter needs no recording notice


def test_servicing_endpoints_enforce_the_rules_and_keep_the_record():
    from tests.test_intake import GOOD, pick_pin
    with KeyedClient(app) as c:
        h = _staff(c)
        r = c.post("/api/applications", json={"scenario_id": "salaried_approve"})
        cid = r.json()["case_id"]
        assert r.json()["decision"]["outcome"] == "APPROVE"
        st = c.get(f"/api/cases/{cid}/statements?months=9").json()
        assert [s["quarter"] for s in st["statements"]] == [1, 2, 3] and st["illustrative"]
        # closure: officer records repayment, then a late release needs a reason
        assert c.post(f"/api/cases/{cid}/closure", json={"repaid_on": "2027-01-01"}, headers={"Authorization": ""}).status_code in (401, 403)
        assert c.post(f"/api/cases/{cid}/closure", json={"repaid_on": "2020-01-01", "released_on": "2020-03-15"}, headers={**h, "X-Case-Key": ""}).status_code == 422
        ok = c.post(f"/api/cases/{cid}/closure", json={"repaid_on": "2020-01-01", "released_on": "2020-02-20", "delay_reason": "charge satisfaction filed late by the registry"}, headers={**h, "X-Case-Key": ""}).json()
        assert ok["status"] == "released" and ok["days_late"] == 20 and ok["compensation_inr"] == 100_000
        # recovery: an agent without paperwork is refused, a proper agent in hours is allowed, an evening call is refused
        for_agents = {**h, "X-Case-Key": ""}
        c.post("/api/recovery-agents", json={"name": "Sahyog Collections", "empanelled_from": "2026-01-01", "empanelled_to": "2030-12-31", "authorisation_ref": "AUTH-7",
                                             "police_verification_date": "2026-01-10", "iibf_certificate": "IIBF-123", "phone": "02212345678"}, headers=for_agents)
        pub = c.get("/api/recovery-agents").json()
        assert any(a["name"] == "Sahyog Collections" and a["current"] for a in pub) and "authorisation_ref" not in pub[0]            # public list: name, period, phone only
        base = {"agent": "Sahyog Collections", "channel": "call", "target": "borrower", "recorded_notice_given": True, "summary": "reminder of the instalment due"}
        good = c.post(f"/api/cases/{cid}/recovery-contact", json={**base, "at": "2027-02-10T10:00:00+05:30"}, headers=for_agents).json()
        late = c.post(f"/api/cases/{cid}/recovery-contact", json={**base, "at": "2027-02-10T20:15:00+05:30"}, headers=for_agents).json()
        ghost = c.post(f"/api/cases/{cid}/recovery-contact", json={**base, "agent": "Unknown Recovery Co", "at": "2027-02-11T10:00:00+05:30"}, headers=for_agents).json()
        assert good["allowed"] and not late["allowed"] and late["violations"][0]["rule"] == "HOURS" and not ghost["allowed"] and ghost["violations"][0]["rule"] == "AGENT"
        from griha import api
        events = [x["event"] for x in api.eng().audit.for_case(cid)]
        assert "RECOVERY_CONTACT" in events and events.count("RECOVERY_CONTACT_REFUSED") == 2


# ---- V-CIP: the procedure of KYC Directions 2025 paras 26 and 27 as enforced code ----
def test_vcip_questions_are_randomised_and_cover_liveness_profile_and_identity():
    from griha import vcip
    sets = [tuple(q["id"] for q in vcip.new_questions()) for _ in range(12)]
    assert len(set(sets)) > 6                                                                          # not a fixed script: the sequence and type vary (27(2)(iii))
    for qs in (vcip.new_questions() for _ in range(20)):
        assert {q["kind"] for q in qs} == {"liveness", "profile", "identity"} and len({q["id"] for q in qs}) == len(qs)


def _good_vcip(questions):
    return {"geo": {"lat": 28.6139, "lon": 77.209, "accuracy": 20}, "identification_method": "aadhaar_otp", "id_obtained_on": "2026-11-11", "photo_sha256": "a" * 64,
            "pan_image_sha256": "b" * 64, "financial_profile_confirmed": True, "liveness_passed": True, "questions": questions,
            "answers": [{"id": q["id"], "ok": True} for q in questions]}


def test_vcip_evaluation_cites_the_paragraph_for_each_missing_element():
    from griha import vcip
    from datetime import date
    qs = vcip.new_questions()
    on = date(2026, 11, 12)                                                                            # a Thursday
    assert vcip.evaluate(_good_vcip(qs), on)["passed"]
    bad = {**_good_vcip(qs), "geo": {}, "photo_sha256": None, "pan_image_sha256": None, "financial_profile_confirmed": False, "liveness_passed": False,
           "answers": [], "identification_method": "selfie_only"}
    r = vcip.evaluate(bad, on)
    assert not r["passed"] and {x["rule"] for x in r["reasons"]} >= {"GEO", "IDENT", "PHOTO", "PAN", "PROFILE", "LIVENESS", "QUESTIONS"}
    assert all("para" in x["cite"] for x in r["reasons"])
    assert vcip.evaluate({**_good_vcip(qs), "pan_image_sha256": None, "epan": True}, on)["passed"]          # an e-PAN replaces the PAN image
    stale = vcip.evaluate({**_good_vcip(qs), "id_obtained_on": "2026-11-05"}, on)                           # 5 working days old
    assert [x["rule"] for x in stale["reasons"]] == ["STALE"]
    fresh = vcip.evaluate({**_good_vcip(qs), "id_obtained_on": "2026-11-09"}, on)                           # Monday -> Thursday is 3 working days: allowed
    assert fresh["passed"]
    pr = vcip.evaluate({**_good_vcip(qs), "prompting_observed": True}, on)
    assert pr["must_reject"] and pr["reasons"][0]["rule"] == "PROMPTING"
    assert vcip.evaluate({**_good_vcip(qs), "disruption": "dropped"}, on)["reasons"][0]["rule"] == "DROPPED"
    assert vcip.evaluate({**_good_vcip(qs), "address_differs": True}, on)["reasons"][0]["rule"] == "ADDRESS"


def test_vcip_endpoints_require_staff_and_cannot_complete_a_session_twice():
    with KeyedClient(app) as c:
        cid = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()["case_id"]
        assert c.post(f"/api/cases/{cid}/vcip/start", headers={"Authorization": ""}).status_code in (401, 403)
        h = {**_staff(c), "X-Case-Key": ""}
        s1 = c.post(f"/api/cases/{cid}/vcip/start", headers=h).json()
        s2 = c.post(f"/api/cases/{cid}/vcip/start", headers=h).json()
        done = _good_vcip(s2["questions"]); done.pop("questions")
        done["id_obtained_on"] = date_today_iso()
        r = c.post(f"/api/cases/{cid}/vcip/{s2['session_id']}/complete", json=done, headers=h)
        assert r.status_code == 200 and r.json()["passed"], r.text
        assert c.post(f"/api/cases/{cid}/vcip/{s2['session_id']}/complete", json=done, headers=h).status_code == 409
        assert c.post(f"/api/cases/{cid}/vcip/{s1['session_id']}/complete", json=done, headers=h).status_code == 404      # only the latest session is open
        assert c.get(f"/api/cases/{cid}/vcip", headers=h).json()["state"] == "passed"


def date_today_iso():
    from datetime import date
    return date.today().isoformat()
