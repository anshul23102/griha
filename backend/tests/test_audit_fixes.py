"""Regression tests for the second judge's audit: hosted-demo behaviour, idempotent submit, Indic names, restated cases, refer breakdown."""
import asyncio

from griha import api
from griha.api import STATE, app
from tests.keyed import KeyedClient
from tests.test_intake import GOOD, pick_pin


def test_indic_joiners_are_allowed_inside_a_name_but_not_at_its_edges():
    with KeyedClient(app) as c:
        pin = pick_pin(c, "Jaipur")
        base = {**GOOD, "pincode": pin}
        assert c.post("/api/applications/new?wait=true", json={**base, "name": "श्रीमती क्‍या शर्मा"}).status_code == 200   # ZWJ between a virama and a letter
        assert c.post("/api/applications/new", json={**base, "name": "‍शर्मा"}).status_code == 422                            # joiner at the start
        assert c.post("/api/applications/new", json={**base, "name": "Meena‮atel"}).status_code == 422                         # bidi override still refused
        assert c.post("/api/applications/new", json={**base, "name": "Meena​ Patel"}).status_code == 422                       # zero-width space still refused


def test_same_idempotency_key_returns_the_first_case_not_a_second():
    with KeyedClient(app) as c:
        f = {**GOOD, "pincode": pick_pin(c, "Jaipur"), "pan": "QWERT1234Y", "phone": "9811122233", "survey_no": "ID-1/1"}
        h = {"Idempotency-Key": "test-key-0001-abcdef"}
        a = c.post("/api/applications/new", json=f, headers=h).json()
        before = len(STATE["cases"])
        b = c.post("/api/applications/new", json=f, headers=h).json()
        assert a["case_id"] == b["case_id"] and len(STATE["cases"]) == before
        d = c.post("/api/applications/new", json=f, headers={"Idempotency-Key": "test-key-0002-abcdef"}).json()
        assert d["case_id"] != a["case_id"]
        assert c.post("/api/applications/new", json=f, headers={"Idempotency-Key": "bad key!"}).status_code == 422


def test_docs_page_may_load_its_cdn_but_no_other_page_may():
    with KeyedClient(app) as c:
        docs = c.get("/docs").headers["content-security-policy"]
        assert "cdn.jsdelivr.net" in docs
        assert "cdn.jsdelivr.net" not in c.get("/api/health").headers["content-security-policy"]


def test_demo_seed_runs_the_prepared_scenarios_once():
    with KeyedClient(app):
        before = len(STATE["cases"])
        asyncio.run(api._seed_demo())
        assert len(STATE["cases"]) - before == len(STATE["scen"]) >= 10


def test_withheld_referral_gets_a_demo_note_only_on_the_public_demo(monkeypatch):
    with KeyedClient(app) as c:
        r = c.post("/api/applications", json={"scenario_id": "sanctions"}).json()
        cid = r["case_id"]
        assert "demo_note" not in c.get(f"/api/cases/{cid}").json()
        monkeypatch.setattr(api, "PUBLIC_DEMO", True)
        v = c.get(f"/api/cases/{cid}").json()
        assert "Lender desk" in v["demo_note"] and "sanction" not in v["demo_note"].lower()          # it explains the mechanism without naming the finding
        ok = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
        assert "demo_note" not in c.get(f"/api/cases/{ok['case_id']}").json()


def test_case_rebuilt_under_a_newer_policy_is_marked_restated(monkeypatch):
    from griha.policy import Policy
    with KeyedClient(app) as c:
        cid = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()["case_id"]
        STATE["cases"].pop(cid)
        monkeypatch.setattr(Policy, "hash", lambda self: "changed-policy-hash")
        api._apply_audit(list(api.eng().audit.for_case(cid)))
        assert STATE["cases"][cid]["restated"]["recorded_policy_hash"] != "changed-policy-hash"
        assert c.get(f"/api/cases/{cid}").json()["restated"]["current_policy_hash"] == "changed-policy-hash"


def test_impact_reports_where_the_humans_come_in():
    with KeyedClient(app) as c:
        m = c.get("/api/impact").json()["measured"]["refer_breakdown"]
        assert set(m["by_queue"]) <= {"CREDIT", "FRAUD", "PROPERTY", "DATA"} and abs(sum(m["by_queue"].values()) - c.get("/api/impact").json()["measured"]["refer_rate"]) < 0.002
        assert m["credit_reasons"]


def test_public_demo_admin_has_its_own_private_password_or_does_not_exist(monkeypatch):
    import importlib

    from griha import auth
    try:
        monkeypatch.setenv("GRIHA_PUBLIC_DEMO", "1")
        monkeypatch.delenv("GRIHA_ADMIN_PASSWORD", raising=False)
        importlib.reload(auth)
        assert "admin@griha.demo" not in auth.USERS and auth.login("admin@griha.demo", "griha-demo") is None      # fail closed: no admin at all
        assert auth.login("officer@griha.demo", "griha-demo")["role"] == "underwriter"                            # the published officer login still works
        monkeypatch.setenv("GRIHA_ADMIN_PASSWORD", "a-private-secret-123")
        importlib.reload(auth)
        assert auth.login("admin@griha.demo", "griha-demo") is None and auth.login("admin@griha.demo", "a-private-secret-123")["role"] == "admin"
        assert auth.login("officer@griha.demo", "a-private-secret-123") is None
    finally:
        monkeypatch.undo()
        importlib.reload(auth)
        assert auth.login("admin@griha.demo", "griha-demo")                                                       # local default restored


def test_prepared_demo_cases_cannot_be_erased_on_the_public_demo(monkeypatch):
    with KeyedClient(app) as c:
        asyncio.run(api._seed_demo())
        monkeypatch.setattr(api, "PUBLIC_DEMO", True)
        h = {"Authorization": "Bearer " + c.post("/api/login", json={"email": "admin@griha.demo", "password": "griha-demo"}).json()["token"], "X-Case-Key": ""}
        seeded = f"A-{api.SEED_PREFIX}0001"
        assert seeded in STATE["cases"]
        r = c.post(f"/api/cases/{seeded}/erase", json={"reason": "a visitor trying to wipe the fixtures"}, headers=h)
        assert r.status_code == 403 and STATE["cases"][seeded].get("erased") is not True


# ---- third audit: real client address, per-caller lockout, trimmed public ops ----
def test_client_ip_trusts_only_the_part_of_the_chain_our_infrastructure_wrote():
    from griha.clientip import client_ip
    edge = "13.32.0.5"                                                  # inside a published CloudFront range
    from griha import clientip
    assert any(__import__("ipaddress").ip_address(edge) in n for n in clientip._edges()), "CloudFront ranges snapshot should cover 13.32.0.0/15"
    assert client_ip("172.17.0.1", f"8.8.4.4, {edge}") == "8.8.4.4"                 # Caddy -> app, CloudFront edge on the right: the viewer is the next address
    assert client_ip("172.17.0.1", f"6.6.6.6, 8.8.4.4, {edge}") == "8.8.4.4"        # a forged value on the left is never reached
    assert client_ip("172.17.0.1", "8.8.4.4") == "8.8.4.4"                           # direct to Caddy: Caddy appended the real peer
    assert client_ip("93.184.216.34", "1.2.3.4") == "93.184.216.34"                            # a direct connection: the header is attacker-controlled and ignored
    assert client_ip("127.0.0.1", None) == "127.0.0.1" and client_ip("172.17.0.1", "garbage, also-garbage") == "172.17.0.1"
    assert client_ip("testclient", "9.9.9.9") == "testclient"                                # not an IP: used as it is


def test_login_lockout_is_per_caller_so_a_stranger_cannot_lock_everyone_out():
    from griha import auth
    for _ in range(auth.LOCKOUT_AFTER):
        assert auth.login("officer@griha.demo", "wrong", "198.51.100.7") is None
    assert auth.locked("officer@griha.demo", "198.51.100.7") > 0                              # the attacker's address is locked out
    assert auth.locked("officer@griha.demo", "203.0.113.77") == 0                              # everyone else is not
    assert auth.login("officer@griha.demo", "griha-demo", "203.0.113.77")["role"] == "underwriter"
    assert not any(k.startswith("officer@griha.demo|203.0.113.77") for k in auth._FAILS)


def test_lockout_and_rate_limit_work_per_visitor_behind_the_proxy():
    from starlette.testclient import TestClient
    c = TestClient(app, client=("172.17.0.1", 5000))                  # the reverse proxy's address, as the container sees it
    with c:
        mine = {"X-Client-Chain": "6.6.6.6, 8.8.8.8, 13.32.0.5", "X-Forwarded-For": "5.5.5.5"}      # Caddy-written chain: CloudFront edge on the right; the plain header is ignored when it is present
        codes = [c.post("/api/login", json={"email": "admin@griha.demo", "password": "bad"}, headers=mine).status_code for _ in range(7)]
        assert codes[:5] == [401] * 5 and codes[5] == 429                                          # this visitor is locked out after five
        other = {"X-Client-Chain": "6.6.6.6, 1.1.1.1, 13.32.0.5"}                       # the same forged left value, a different real visitor
        assert c.post("/api/login", json={"email": "admin@griha.demo", "password": "griha-demo"}, headers=other).status_code == 200   # another visitor is unaffected


def test_public_demo_hides_internals_from_anonymous_visitors_but_not_from_staff(monkeypatch):
    with KeyedClient(app) as c:
        monkeypatch.setattr(api, "PUBLIC_DEMO", True)
        o = c.get("/api/ops", headers={"Authorization": ""}).json()
        assert set(o["orchestrator"]) <= {"mode", "requested"} and "grafana_url" not in o["monitoring"] and "model" not in o["llm"]
        assert c.get("/api/metrics", headers={"Authorization": ""}).status_code == 401
        h = {"Authorization": "Bearer " + c.post("/api/login", json={"email": "officer@griha.demo", "password": "griha-demo"}).json()["token"]}
        assert "client_ip" not in o and "client_ip" in c.get("/api/ops", headers=h).json()
        assert "grafana_url" in c.get("/api/ops", headers=h).json()["monitoring"] and c.get("/api/metrics", headers=h).status_code == 200
    monkeypatch.setattr(api, "PUBLIC_DEMO", False)
    with KeyedClient(app) as c:
        assert c.get("/api/metrics", headers={"Authorization": ""}).status_code == 200                # local Prometheus scrape still works
