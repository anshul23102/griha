import pytest
from fastapi.testclient import TestClient
from tests.keyed import KeyedClient

from griha.api import app


@pytest.fixture(scope="module")
def client():
    with KeyedClient(app) as c:
        yield c


def token(c, email="officer@griha.demo"):
    r = c.post("/api/login", json={"email": email, "password": "griha-demo"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_scenarios_and_apply(client):
    sc = client.get("/api/scenarios").json()
    assert len(sc) == 10
    outcomes = {}
    for s in sc:
        r = client.post("/api/applications", json={"scenario_id": s["id"]})
        assert r.status_code == 200, s["id"]
        outcomes[s["id"]] = r.json()["decision"]["outcome"]
    assert outcomes["salaried_approve"] == "APPROVE" and outcomes["sanctions"] == "REFER"
    assert outcomes["fraud_edit"] == "REFER" and outcomes["fraud_ring"] == "REFER"


def test_pii_masked(client):
    c = client.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    assert "XXXX" in c["applicant"]["pan"] and "dob" not in c["applicant"]


def test_auth_required_and_four_eyes(client):
    assert client.get("/api/cases").status_code == 401
    h = token(client)
    c = client.post("/api/applications", json={"scenario_id": "fraud_edit"}).json()
    body = {"action": "approve", "reason": "Customer provided originals, verified in branch."}
    assert client.post(f"/api/cases/{c['case_id']}/review", json=body, headers=h).status_code == 403
    assert client.post(f"/api/cases/{c['case_id']}/review", json=body, headers=token(client, "admin@griha.demo")).status_code == 200
    assert client.get("/api/audit/verify", headers=h).json()["ok"] is True


def test_path_to_yes_for_gap(client):
    c = client.post("/api/applications", json={"scenario_id": "refer_gap"}).json()
    p = client.post(f"/api/cases/{c['case_id']}/path-to-yes").json()
    assert p and p[0]["lever"] in ("reduce_amount", "extend_tenure", "co_applicant", "none")


def test_simulator_and_replay(client):
    h = token(client)
    r = client.post("/api/simulate", json={"changes": {"params.foir_cap": 0.65}}, headers=h).json()
    assert r["scenario"]["approve_rate"] >= r["baseline"]["approve_rate"]
    c = client.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
    assert client.post(f"/api/audit/replay/{c['case_id']}", headers=h).json()["match"] is True
    assert client.post("/api/simulate", json={"changes": {"rules.0.id": "x"}}, headers=h).status_code == 422
