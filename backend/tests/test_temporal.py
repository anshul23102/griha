import os
import shutil
import socket
import subprocess
import time

import pytest
from fastapi.testclient import TestClient
from tests.keyed import KeyedClient

pytestmark = pytest.mark.skipif(shutil.which("temporal") is None, reason="temporal CLI not installed")


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def client():
    port, ui = _port(), _port()
    proc = subprocess.Popen(["temporal", "server", "start-dev", "--headless", "--ip", "127.0.0.1", "--port", str(port), "--ui-port", str(ui)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.skip("temporal dev server did not start")
    old = {k: os.environ.get(k) for k in ("GRIHA_ORCHESTRATOR", "TEMPORAL_ADDRESS")}
    os.environ.update(GRIHA_ORCHESTRATOR="temporal", TEMPORAL_ADDRESS=f"127.0.0.1:{port}")
    from griha import runtime
    from griha.api import app
    runtime.SLA_SECONDS = 2
    try:
        with KeyedClient(app) as c:
            o = c.get("/api/ops").json()["orchestrator"]
            assert o["mode"] == "temporal", o
            yield c
    finally:
        for k, v in old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        proc.terminate()


def tok(c, email="officer@griha.demo"):
    return {"Authorization": "Bearer " + c.post("/api/login", json={"email": email, "password": "griha-demo"}).json()["token"]}


FORM = {"name": "Temporal Test", "dob": "1988-04-12", "pan": "ABCDE1234F", "phone": "9876543210", "gender": "F", "employment": "salaried",
        "employer": "Metro Hospital", "monthly_income": 62000, "existing_emi": 4000, "city": "Jaipur", "product": "HL", "amount": 2400000,
        "tenure_months": 240, "property_type": "apartment", "area_sqft": 950, "property_age_years": 6, "declared_value": 3600000,
        "survey_no": "KH-221/4", "consent": True}


def form(c, **kw):
    pin = next(x for x in c.get("/api/reference").json()["cities"] if x["name"] == "Jaipur")["pins"][0]
    return {**FORM, "pincode": pin, **kw}


def test_case_runs_as_a_workflow_and_replays_identically(client):
    case = client.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    assert case["workflow"]["orchestrator"] == "temporal" and case["workflow"]["id"] == f"uw-{case['case_id']}"
    assert case["decision"]["outcome"] == "APPROVE"
    # the in-process engine must reproduce the Temporal-produced decision exactly
    assert client.post(f"/api/audit/replay/{case['case_id']}", headers=tok(client)).json()["match"] is True
    ops = client.get("/api/ops").json()
    assert ops["orchestrator"]["workflows_total"] >= 1 and ops["metrics"]["decisions"] >= 1


def test_real_progress_via_workflow_query(client):
    r = client.post("/api/applications/new?wait=false", json=form(client)).json()
    assert r["state"] == "running"
    seen, state = set(), None
    for _ in range(80):
        p = client.get(f"/api/cases/{r['case_id']}/progress").json()
        state = p["state"]
        seen |= {s["stage"] for s in p.get("stages", [])}
        if state == "done":
            break
        time.sleep(0.05)
    assert state == "done"
    assert client.get(f"/api/cases/{r['case_id']}").json()["decision"]["evidence"][-1]["stage"] == "compliance"


def test_flaky_bureau_is_retried_then_succeeds_and_hard_outage_refers(client):
    ok = client.post("/api/applications/new", json=form(client, simulate_outage="bureau_flaky")).json()
    bureau = next(s for s in next(e for e in ok["decision"]["evidence"] if e["stage"] == "data_integration")["data"]["sources"] if s["id"] == "bureau")
    assert bureau["status"] == "ok" and bureau["attempts"] == 3
    down = client.post("/api/applications/new", json=form(client, simulate_outage="bureau")).json()
    assert down["decision"]["outcome"] == "REFER" and down["decision"]["refer_queue"] == "DATA"
    bureau = next(s for s in next(e for e in down["decision"]["evidence"] if e["stage"] == "data_integration")["data"]["sources"] if s["id"] == "bureau")
    assert bureau["status"] == "failed"
    snap = client.get("/api/ops").json()["metrics"]["activity_retries"]
    assert snap.get("fetch_bureau", 0) >= 2


def test_review_is_a_durable_update_with_sla_escalation(client):
    case = client.post("/api/applications", json={"scenario_id": "refer_gap"}).json()
    cid = case["case_id"]
    assert case["decision"]["outcome"] == "REFER" and case["workflow"]["sla"]["escalated"] is False
    time.sleep(3.5)   # SLA is 2 s in this test
    after = client.get(f"/api/cases/{cid}").json()
    assert after["workflow"]["sla"]["escalated"] is True
    h = tok(client)
    body = {"action": "decline", "reason": "Gap too large, advised to reapply smaller."}
    done = client.post(f"/api/cases/{cid}/review", json=body, headers=h).json()
    assert done["status"] == "declined_by_officer" and done["reviews"][0]["hash"]
    assert client.post(f"/api/cases/{cid}/review", json=body, headers=h).status_code == 409
    events = [e["event"] for e in done["audit"]]
    assert "SLA_ESCALATION" in events and "HUMAN_REVIEW" in events
