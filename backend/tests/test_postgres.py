"""The audit log and the key vault on PostgreSQL (GRIHA_DATABASE_URL), against a throwaway cluster the test starts itself. Skipped where Postgres is not installed."""
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time

import pytest

from griha import db

pytestmark = pytest.mark.skipif(not (shutil.which("initdb") and shutil.which("pg_ctl")), reason="PostgreSQL server binaries not installed")


@pytest.fixture(scope="module")
def pg_url():
    d = tempfile.mkdtemp(prefix="griha-pg-")
    env = {**os.environ, "LC_ALL": "C", "LANG": "C"}                       # Postgres refuses to start under an unset or invalid locale
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    subprocess.run(["initdb", "-D", d, "-A", "trust", "-U", "griha", "--locale=C", "-E", "UTF8"], check=True, capture_output=True, env=env)
    subprocess.run(["pg_ctl", "-D", d, "-o", f"-p {port} -k /tmp -c listen_addresses=127.0.0.1", "-l", d + "/log", "-w", "start"], check=True, capture_output=True, env=env)
    try:
        subprocess.run(["createdb", "-h", "127.0.0.1", "-p", str(port), "-U", "griha", "griha_test"], check=True, capture_output=True, env=env)
        yield f"postgresql://griha@127.0.0.1:{port}/griha_test"
    finally:
        subprocess.run(["pg_ctl", "-D", d, "-m", "immediate", "stop"], capture_output=True, env=env)
        shutil.rmtree(d, ignore_errors=True)


def test_audit_chain_and_vault_work_on_postgres_and_survive_concurrent_writers(pg_url, monkeypatch):
    from griha.audit import AuditLog
    from griha.crypto import Vault
    monkeypatch.setenv("GRIHA_DATABASE_URL", pg_url)
    assert db.backend() == "postgresql"
    a = AuditLog()
    a2 = AuditLog()                                                          # a second connection: another worker process on another host
    errors = []

    def work(log, tag):
        try:
            for i in range(25):
                log.append(f"C-{tag}", "DECISION", {"i": i, "tag": tag})
        except Exception as e:                                               # noqa: BLE001
            errors.append(e)
    ts = [threading.Thread(target=work, args=(a, "A")), threading.Thread(target=work, args=(a2, "B"))]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert not errors
    v = a.verify()
    assert v["ok"] and v["entries"] == 50                                    # one unbroken hash chain, no lost or duplicate sequence numbers
    assert len(a.for_case("C-A")) == 25 and len(a2.for_case("C-B")) == 25
    # tampering with a stored row breaks the chain, as on SQLite
    a._db.execute("UPDATE audit SET payload = ? WHERE seq = 3", ('{"i":999}',))
    assert not AuditLog().verify()["ok"]
    # the key vault: one data key per case, wrapped; erasure destroys it
    vault = Vault.from_env(__import__("pathlib").Path(tempfile.mkdtemp()))
    k1 = vault.encrypt("C-X", b"secret", b"t")
    assert vault.decrypt("C-X", k1, b"t") == b"secret"
    assert vault.erase("C-X")
    with pytest.raises(Exception):
        vault.decrypt("C-X", k1, b"t")
