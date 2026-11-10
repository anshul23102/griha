import json
import os

import pytest
from fastapi.testclient import TestClient
from tests.keyed import KeyedClient

from griha.audit import AuditLog
from griha.crypto import ErasedError, Vault
from griha.engine import Engine
from griha.synth import make_case


def test_round_trip_and_binding():
    v = Vault.ephemeral()
    t = v.encrypt("C1", b"PAN ABCDE1234F", b"x")
    assert b"ABCDE" not in t.encode() and v.decrypt("C1", t, b"x") == b"PAN ABCDE1234F"
    with pytest.raises(ValueError):
        v.decrypt("C1", t, b"other-context")           # wrong associated data
    v.encrypt("C2", b"other")
    with pytest.raises(ValueError):
        v.decrypt("C2", t, b"x")                       # ciphertext moved to another case
    flipped = t[:-4] + ("AAAA" if not t.endswith("AAAA") else "BBBB")
    with pytest.raises(ValueError):
        v.decrypt("C1", flipped, b"x")                 # bit-flip detected by GCM


def test_erasure_shreds_data_but_not_other_cases():
    v = Vault.ephemeral()
    a, b = v.encrypt("A", b"secret-a"), v.encrypt("B", b"secret-b")
    assert v.erase("A") and not v.has("A")
    with pytest.raises(ErasedError):
        v.decrypt("A", a)
    assert v.decrypt("B", b) == b"secret-b"


def test_master_key_rotation_rewraps_without_touching_ciphertext(tmp_path):
    v = Vault(os.urandom(32), tmp_path / "ks.db")
    tok = v.encrypt("A", b"hello")
    new = os.urandom(32)
    assert v.rewrap(new) == 1
    assert v.decrypt("A", tok) == b"hello"
    reopened = Vault(new, tmp_path / "ks.db")
    assert reopened.decrypt("A", tok) == b"hello"
    assert oct(os.stat(tmp_path / "ks.db").st_mode)[-3:] == "600"


def test_keystore_holds_only_wrapped_keys(tmp_path):
    v = Vault(os.urandom(32), tmp_path / "ks.db")
    v.encrypt("A", b"x")
    import sqlite3
    rows = sqlite3.connect(tmp_path / "ks.db").execute("SELECT subject, wrapped FROM keys").fetchall()
    assert [r[0] for r in rows] == ["A"] and len(rows[0][1]) > 40 and b"x" not in rows[0][1].encode()[:1]


def test_audit_log_contains_no_plaintext_pii_and_still_replays():
    eng = Engine(audit=AuditLog(None), vault=Vault.ephemeral())
    app, _ = make_case(777)
    eng.underwrite(app, record=True)
    raw = json.dumps(eng.audit.entries)
    for secret in (app.applicant.pan, app.applicant.name, app.applicant.phone):
        assert secret not in raw
    assert eng.audit.verify()["ok"]
    assert eng.replay(eng.audit.entries[-1])["match"] is True


def test_erasure_keeps_chain_valid_and_replay_reports_erased():
    eng = Engine(audit=AuditLog(None), vault=Vault.ephemeral())
    app, _ = make_case(778)
    eng.underwrite(app, record=True)
    eng.vault.erase(app.case_id)
    eng.audit.append(app.case_id, "ERASURE", {"by": "admin", "reason": "subject request"})
    assert eng.audit.verify()["ok"]
    r = eng.replay(eng.audit.entries[0])
    assert r["erased"] is True and r["recorded_outcome"]


def test_api_erase_requires_admin_and_hides_data():
    from griha.api import app as api
    with KeyedClient(api) as c:
        tok = lambda e: {"Authorization": "Bearer " + c.post("/api/login", json={"email": e, "password": "griha-demo"}).json()["token"]}
        case = c.post("/api/applications", json={"scenario_id": "salaried_approve"}).json()
        cid, body = case["case_id"], {"reason": "Data subject requested deletion"}
        assert c.post(f"/api/cases/{cid}/erase", json=body).status_code == 401
        assert c.post(f"/api/cases/{cid}/erase", json=body, headers=tok("officer@griha.demo")).status_code == 403
        r = c.post(f"/api/cases/{cid}/erase", json=body, headers=tok("admin@griha.demo")).json()
        assert r["erased"] is True and "applicant" not in r and "statement" not in r
        assert c.get(f"/api/cases/{cid}").json()["erased"] is True
        assert c.post(f"/api/cases/{cid}/erase", json=body, headers=tok("admin@griha.demo")).status_code == 409
        assert c.get("/api/audit/verify", headers=tok("officer@griha.demo")).json()["ok"] is True
        assert c.post(f"/api/audit/replay/{cid}", headers=tok("officer@griha.demo")).json()["erased"] is True


def test_two_handles_racing_to_create_a_key_end_up_with_the_same_key(tmp_path):
    """Two workers encrypt the first record of the same case at the same moment: either one's ciphertext must open with the other's handle."""
    import threading
    mk = os.urandom(32)
    a, b = Vault(mk, tmp_path / "ks.db"), Vault(mk, tmp_path / "ks.db")
    out = {}
    def go(name, v):
        out[name] = v.encrypt("CASE-1", name.encode(), b"x")
    ts = [threading.Thread(target=go, args=(n, v)) for n, v in (("a", a), ("b", b)) for _ in range(5)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert a.decrypt("CASE-1", out["b"], b"x") == b"b" and b.decrypt("CASE-1", out["a"], b"x") == b"a"


def test_erasure_by_one_handle_is_immediate_for_the_other(tmp_path):
    mk = os.urandom(32)
    a, b = Vault(mk, tmp_path / "ks.db"), Vault(mk, tmp_path / "ks.db")
    tok = a.encrypt("C", b"secret")
    assert b.decrypt("C", tok) == b"secret"
    assert a.erase("C")
    with pytest.raises(ErasedError):
        b.decrypt("C", tok)


def test_legacy_keystore_json_is_imported_once(tmp_path):
    mk = os.urandom(32)
    old = Vault(mk, tmp_path / "x.db")
    tok = old.encrypt("A", b"kept")
    rows = dict(__import__("sqlite3").connect(tmp_path / "x.db").execute("SELECT subject, wrapped FROM keys").fetchall())
    (tmp_path / "keystore.json").write_text(json.dumps(rows))
    fresh = Vault(mk, tmp_path / "keystore.db")
    assert fresh.decrypt("A", tok) == b"kept" and not (tmp_path / "keystore.json").exists() and (tmp_path / "keystore.json.migrated").exists()


def test_master_and_session_keys_survive_a_simultaneous_first_start(tmp_path, monkeypatch):
    import threading
    monkeypatch.delenv("GRIHA_MASTER_KEY", raising=False)
    monkeypatch.delenv("GRIHA_SECRET", raising=False)
    vaults, errs = [], []
    def start():
        try:
            vaults.append(Vault.from_env(tmp_path))
        except Exception as e:
            errs.append(e)
    ts = [threading.Thread(target=start) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs and len(vaults) == 8
    tok = vaults[0].encrypt("C", b"v")
    assert all(v.decrypt("C", tok) == b"v" for v in vaults)           # every worker derived the same master key
    from griha import auth, config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "s")
    keys, errs2 = [], []
    def sk():
        try:
            keys.append(auth._persistent_secret())
        except Exception as e:
            errs2.append(e)
    ts = [threading.Thread(target=sk) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errs2 and len(set(keys)) == 1
