"""One way to open SQLite for every store (audit log, key vault): private file, WAL, durable commits, and a startup that is safe when
several worker processes initialise the same fresh file at the same moment (the journal-mode switch can report 'database is locked'
even with a busy timeout, so initialisation is retried)."""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path


def open_db(path: Path | None, schema: str) -> sqlite3.Connection:
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
