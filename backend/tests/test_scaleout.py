"""Two API workers sharing one audit database must agree: the case table is a projection of the shared log, not private memory."""
import importlib

import pytest

from tests.keyed import KeyedClient


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """The API module reloaded over an empty data directory, and reloaded again afterwards so other tests see their own."""
    monkeypatch.setenv("GRIHA_DATA_DIR", str(tmp_path))
    import griha.api as api
    import griha.config as config
    importlib.reload(config)
    importlib.reload(api)
    yield api, config
    monkeypatch.undo()
    importlib.reload(config)
    importlib.reload(api)


def _login(c, email):
    return {"Authorization": "Bearer " + c.post("/api/login", json={"email": email, "password": "griha-demo"}).json()["token"]}


def test_a_case_made_by_one_worker_is_served_and_reviewed_by_another(fresh):
    api, config = fresh
    worker_a, worker_b = KeyedClient(api.app), KeyedClient(api.app)
    # Two separate application states over the same data directory stand in for two worker processes.
    with worker_a as a:
        made = a.post("/api/applications", json={"scenario_id": "refer_gap"}).json()
        cid, key = made["case_id"], made["access_key"]
        state_a = dict(api.STATE)
    api.STATE.clear()
    with worker_b as b:                                                  # starts later: rehydrates from the shared database
        assert b.get(f"/api/cases/{cid}", headers={"X-Case-Key": key}).status_code == 200
        r = b.post(f"/api/cases/{cid}/review", headers=_login(b, "officer@griha.demo"), json={"action": "decline", "reason": "Income proof is unclear"})
        assert r.status_code == 200 and r.json()["status"] == "declined_by_officer"
        later = b.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()["case_id"]
        assert later in {x["case_id"] for x in b.get("/api/cases", headers=_login(b, "officer@griha.demo")).json()}
    assert state_a  # worker A's own table existed before B started


def test_sync_picks_up_cases_written_after_startup(fresh):
    api, config = fresh
    from griha.audit import AuditLog
    with KeyedClient(api.app) as late:                                   # this worker is already running...
        other = AuditLog(config.AUDIT_PATH)                              # ...when another process records a decision in the shared database
        e = api.eng()
        from griha.synth import make_case
        app, _ = make_case(64000)
        app.case_id = "A-SYNC0001"
        e2 = type(e)(audit=other, vault=e.vault)
        e2.underwrite(app, record=True)
        assert "A-SYNC0001" not in api.STATE["cases"]
        late.get("/api/stats")                                           # any list or stats call catches up
        assert "A-SYNC0001" in api.STATE["cases"]
