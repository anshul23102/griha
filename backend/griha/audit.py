"""Append-only, hash-chained audit log stored in SQLite (WAL). Any edit to a past entry breaks every later hash.

The table is the source of truth: cases are rebuilt from it after a restart (event sourcing), so the audit log is also the database.
Writes happen inside a BEGIN IMMEDIATE transaction that reads the current head hash, so several processes can append to the same file
without forking the chain. For many machines the same schema moves to Postgres (SELECT ... FOR UPDATE on the head row)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

from .db import open_db


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


GENESIS = "0" * 64


def _digest(body: dict) -> str:
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def verify_entries(entries: list[dict]) -> dict:
    """Check a sequence of entries: each must link to the one before and hash to its recorded value."""
    prev = GENESIS
    for i, e in enumerate(entries):
        body = {k: v for k, v in e.items() if k != "hash"}
        if e["prev"] != prev or _digest(body) != e["hash"]:
            return {"ok": False, "broken_at": i, "entries": len(entries)}
        prev = e["hash"]
    return {"ok": True, "broken_at": None, "entries": len(entries), "head": prev}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
  seq INTEGER PRIMARY KEY, ts REAL NOT NULL, case_id TEXT NOT NULL, event TEXT NOT NULL,
  payload TEXT NOT NULL, prev TEXT NOT NULL, hash TEXT NOT NULL UNIQUE);
CREATE INDEX IF NOT EXISTS audit_case ON audit (case_id, event);
"""


def _row(r) -> dict:
    return {"seq": r[0], "ts": r[1], "case_id": r[2], "event": r[3], "payload": json.loads(r[4]), "prev": r[5], "hash": r[6]}


class AuditLog:
    GENESIS = GENESIS

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._cache: list[dict] = []
        self._db = open_db(self.path, _SCHEMA)
        if self.path:
            self._import_legacy_jsonl()

    def _import_legacy_jsonl(self) -> None:
        """One-time import of the old audit.jsonl next to the database, preserving every hash. The file is kept, renamed."""
        legacy = self.path.with_name("audit.jsonl")
        if not legacy.exists() or self._db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]:
            return
        rows = [json.loads(l) for l in legacy.read_text().splitlines() if l.strip()]
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.executemany("INSERT INTO audit VALUES (?,?,?,?,?,?,?)",
                                 [(e["seq"], e["ts"], e["case_id"], e["event"], canonical(e["payload"]), e["prev"], e["hash"]) for e in rows])
            self._db.execute("COMMIT")
        legacy.rename(legacy.with_name("audit.jsonl.migrated"))
        os.chmod(legacy.with_name("audit.jsonl.migrated"), 0o600)

    def _refresh(self) -> None:
        last = self._cache[-1]["seq"] if self._cache else -1
        for r in self._db.execute("SELECT seq, ts, case_id, event, payload, prev, hash FROM audit WHERE seq > ? ORDER BY seq", (last,)):
            self._cache.append(_row(r))

    @property
    def entries(self) -> list[dict]:
        with self._lock:
            self._refresh()
            return self._cache

    def count(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]

    def append(self, case_id: str, event: str, payload: dict) -> dict:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")                           # one writer at a time, across processes
            try:
                head = self._db.execute("SELECT seq, hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
                seq, prev = (head[0] + 1, head[1]) if head else (0, GENESIS)
                body = {"seq": seq, "ts": time.time(), "case_id": case_id, "event": event, "payload": payload, "prev": prev}
                body["hash"] = _digest(body)
                self._db.execute("INSERT INTO audit VALUES (?,?,?,?,?,?,?)", (seq, body["ts"], case_id, event, canonical(payload), prev, body["hash"]))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._refresh()
            return body

    def verify(self) -> dict:
        """Verify what is stored, not a cache."""
        rows = [_row(r) for r in self._db.execute("SELECT seq, ts, case_id, event, payload, prev, hash FROM audit ORDER BY seq")]
        return verify_entries(rows)

    def for_case_event(self, case_id: str, event: str) -> list[dict]:
        q = "SELECT seq, ts, case_id, event, payload, prev, hash FROM audit WHERE case_id=? AND event=? ORDER BY seq"
        return [_row(r) for r in self._db.execute(q, (case_id, event))]

    def for_case(self, case_id: str) -> list[dict]:
        q = "SELECT seq, ts, case_id, event, payload, prev, hash FROM audit WHERE case_id=? ORDER BY seq"
        return [_row(r) for r in self._db.execute(q, (case_id,))]
