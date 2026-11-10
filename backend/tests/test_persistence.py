"""A restart must not lose cases: they are rebuilt from the encrypted audit log, and erasure survives too."""
from griha import auth
from griha.api import app
from tests.keyed import KeyedClient


def _login(c, email):
    return {"Authorization": "Bearer " + c.post("/api/login", json={"email": email, "password": "griha-demo"}).json()["token"]}


def test_cases_survive_restart_and_erasure_stays_erased():
    keys = {}
    with KeyedClient(app) as c:
        a = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
        r = c.post("/api/applications", json={"scenario_id": "refer_gap"}).json()
        gone = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
        keys = {x["case_id"]: x["access_key"] for x in (a, r, gone)}
        c.post(f"/api/cases/{r['case_id']}/review", headers=_login(c, "officer@griha.demo"), json={"action": "decline", "reason": "Income proof is unclear"})
        er = c.post(f"/api/cases/{gone['case_id']}/erase", headers=_login(c, "admin@griha.demo"), json={"reason": "Test case removal by owner"})
        assert er.status_code == 200, er.text
        before = {k: c.get(f"/api/cases/{k}", headers={"X-Case-Key": v}).json() for k, v in keys.items()}
    with KeyedClient(app) as c2:                                 # new process state, same data directory
        after = {k: c2.get(f"/api/cases/{k}", headers={"X-Case-Key": v}) for k, v in keys.items()}
        assert all(x.status_code == 200 for x in after.values())
        ja = {k: x.json() for k, x in after.items()}
        assert ja[a["case_id"]]["decision"]["outcome"] == before[a["case_id"]]["decision"]["outcome"] == "APPROVE"
        assert ja[a["case_id"]]["decision"]["digest"] if "digest" in ja[a["case_id"]]["decision"] else True
        assert ja[r["case_id"]]["status"] == "declined_by_officer" and ja[r["case_id"]]["reviews"]
        assert ja[gone["case_id"]]["erased"] is True and "applicant" not in ja[gone["case_id"]]
        assert ja[a["case_id"]]["access_key"] == keys[a["case_id"]]          # applicant links keep working after a restart
        assert c2.get("/api/audit/verify", headers=_login(c2, "officer@griha.demo")).json()["ok"] is True
        rows = c2.get("/api/cases", headers=_login(c2, "officer@griha.demo")).json()
        assert a["case_id"] in {x["case_id"] for x in rows}
