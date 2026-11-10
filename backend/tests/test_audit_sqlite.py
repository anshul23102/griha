"""The audit log lives in SQLite: tamper-evident, durable across reopen, safe for concurrent writers, and importable from the old JSONL."""
import json
import sqlite3
import threading

from griha.audit import AuditLog, canonical, verify_entries


def test_chain_verifies_and_survives_reopen(tmp_path):
    db = tmp_path / "audit.db"
    a = AuditLog(db)
    for i in range(5):
        a.append(f"C{i % 2}", "DECISION", {"i": i, "f": 0.1 + i, "nested": {"x": [1, 2, 3]}})
    assert a.verify()["ok"] and a.count() == 5
    b = AuditLog(db)                                             # a new process opening the same file
    assert b.verify() == a.verify() and [e["hash"] for e in b.entries] == [e["hash"] for e in a.entries]
    assert [e["seq"] for e in b.for_case("C0")] == [0, 2, 4] and len(b.for_case_event("C1", "DECISION")) == 2


def test_editing_a_stored_row_is_detected(tmp_path):
    db = tmp_path / "audit.db"
    a = AuditLog(db)
    for i in range(4):
        a.append("C", "DECISION", {"outcome": "REFER", "i": i})
    raw = sqlite3.connect(db)
    raw.execute("UPDATE audit SET payload=? WHERE seq=1", (canonical({"outcome": "APPROVE", "i": 1}),))
    raw.commit()
    raw.close()
    v = AuditLog(db).verify()
    assert v["ok"] is False and v["broken_at"] == 1


def test_concurrent_writers_from_two_handles_keep_one_chain(tmp_path):
    db = tmp_path / "audit.db"
    logs = [AuditLog(db), AuditLog(db)]                           # two handles stand in for two processes
    def work(k):
        for i in range(40):
            logs[k].append(f"W{k}", "EVT", {"i": i})
    ts = [threading.Thread(target=work, args=(k,)) for k in (0, 1)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    v = AuditLog(db).verify()
    assert v["ok"] and v["entries"] == 80
    assert [e["seq"] for e in AuditLog(db).entries] == list(range(80))


def test_legacy_jsonl_is_imported_once_with_hashes_intact(tmp_path):
    old = AuditLog(None)
    for i in range(3):
        old.append("C", "DECISION", {"i": i})
    (tmp_path / "audit.jsonl").write_text("\n".join(canonical(e) for e in old.entries) + "\n")
    a = AuditLog(tmp_path / "audit.db")
    assert a.verify()["ok"] and a.count() == 3 and [e["hash"] for e in a.entries] == [e["hash"] for e in old.entries]
    assert not (tmp_path / "audit.jsonl").exists() and (tmp_path / "audit.jsonl.migrated").exists()
    a.append("C", "DECISION", {"i": 3})
    assert AuditLog(tmp_path / "audit.db").verify()["ok"]          # a second open does not import again


def test_files_are_private_and_pure_verify_matches():
    import os, tempfile
    d = tempfile.mkdtemp()
    a = AuditLog(os.path.join(d, "audit.db"))
    a.append("C", "E", {})
    assert oct(os.stat(os.path.join(d, "audit.db")).st_mode)[-3:] == "600" and oct(os.stat(d).st_mode)[-3:] == "700"
    assert verify_entries(a.entries) == a.verify()


def test_many_processes_can_initialise_a_fresh_database_at_once(tmp_path):
    """The load test showed 'database is locked' when several workers started on an empty file. Real processes, not threads."""
    import subprocess, sys, textwrap
    code = textwrap.dedent(f"""
        from pathlib import Path
        from griha.audit import AuditLog
        from griha.crypto import Vault
        import os
        a = AuditLog(Path({str(tmp_path)!r}) / 'audit.db')
        v = Vault(bytes(range(32)), Path({str(tmp_path)!r}) / 'keystore.db')
        a.append('C' + str(os.getpid()), 'E', {{}})
        v.encrypt('C' + str(os.getpid()), b'x')
    """)
    procs = [subprocess.Popen([sys.executable, "-c", code], stderr=subprocess.PIPE) for _ in range(6)]
    errs = [p.communicate()[1].decode() for p in procs]
    assert all(p.returncode == 0 for p in procs), errs
    log = AuditLog(tmp_path / "audit.db")
    assert log.verify()["ok"] and log.count() == 6
