"""One way to open SQLite for every store (audit log, key vault): private file, WAL, durable commits, and a startup that is safe when
several worker processes initialise the same fresh file at the same moment (the journal-mode switch can report 'database is locked'
even with a busy timeout, so initialisation is retried)."""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


class PgConn:
    """The few SQLite calls the audit log and the key vault make, mapped onto PostgreSQL, so that GRIHA_DATABASE_URL=postgresql://... switches both stores to Postgres.

    What changes: placeholders (? to %s), INSERT OR IGNORE, REAL to DOUBLE PRECISION in the schema, and BEGIN IMMEDIATE: a transaction that first takes a Postgres
    advisory lock, which is the same "one writer at a time, across processes and hosts" guarantee SQLite gave through its file lock. Each store still holds its own thread lock
    around a transaction, because one connection is shared by the request threads of a process."""

    LOCK_KEY = 7_236_001

    def __init__(self, url: str, schema: str):
        import psycopg                                                    # optional dependency: only needed when a Postgres URL is set
        self._c = psycopg.connect(url, autocommit=True)
        for stmt in [x for x in schema.replace("REAL", "DOUBLE PRECISION").split(";") if x.strip()]:
            self._c.execute(stmt)

    def execute(self, sql: str, params: tuple = ()):
        q = sql.strip()
        up = q.upper()
        if up.startswith("BEGIN"):
            self._c.execute("BEGIN")
            self._c.execute("SELECT pg_advisory_xact_lock(%s)", (self.LOCK_KEY,))
            return None
        if up in ("COMMIT", "ROLLBACK"):
            return self._c.execute(q)
        if up.startswith("INSERT OR IGNORE"):
            q = "INSERT" + q[len("INSERT OR IGNORE"):] + " ON CONFLICT DO NOTHING"
        return self._c.execute(q.replace("?", "%s"), params)


def backend() -> str:
    return "postgresql" if os.environ.get("GRIHA_DATABASE_URL", "").startswith(("postgres://", "postgresql://")) else "sqlite"


def open_db(path: Path | None, schema: str):
    url = os.environ.get("GRIHA_DATABASE_URL", "")
    if url.startswith(("postgres://", "postgresql://")):
        return PgConn(url, schema)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)           # create 0600 before SQLite opens it
        os.close(fd)
    db = sqlite3.connect(str(path) if path else ":memory:", check_same_thread=False, isolation_level=None, timeout=30)
    deadline = time.time() + 30
    while True:
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")                   # a record is durable before the call that wrote it returns
            db.executescript(schema)
            break
        except sqlite3.OperationalError as e:
            if "locked" not in str(e) or time.time() > deadline:
                raise
            time.sleep(0.05)
    if path:
        for suffix in ("", "-wal", "-shm"):
            f = Path(str(path) + suffix)
            if f.exists():
                os.chmod(f, 0o600)
    return db
