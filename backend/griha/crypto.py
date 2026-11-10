"""Envelope encryption with per-subject keys and crypto-shredding.

- A random 256-bit data key (DEK) is created per case and used with AES-256-GCM.
- DEKs are stored only wrapped (encrypted) in SQLite under a master key (KEK) from GRIHA_MASTER_KEY or data/master.key.
- Ciphertext is bound to its case via AES-GCM associated data, so it cannot be moved between cases.
- Erasure (DPDP right to erasure) deletes the wrapped DEK. The hash-chained audit log stays intact and verifiable,
  but the personal data inside it becomes mathematically unrecoverable.
- Master key rotation re-wraps the small DEKs only; no case data is re-encrypted.
Caveat: backups of the keystore taken before erasure would keep the data readable. Back up the keystore with the same retention rules."""
from __future__ import annotations

import base64
import json
import os
import threading
import time
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import open_db

VERSION = "v1"


class ErasedError(Exception):
    """The data key for this subject was destroyed: the data is gone by design."""


class Vault:
    """Keys live in SQLite (table keys: subject, wrapped). Every operation reads the database, so an erasure by one worker takes effect in
    all of them at once, and creating a case key is an atomic get-or-create: when two workers race, both end up with the same key."""

    def __init__(self, master_key: bytes, store_path: Path | None = None):
        if len(master_key) != 32:
            raise ValueError("master key must be 32 bytes")
        self._kek = AESGCM(master_key)
        self.path = store_path
        self._lock = threading.Lock()
        self._db = open_db(store_path, "CREATE TABLE IF NOT EXISTS keys (subject TEXT PRIMARY KEY, wrapped TEXT NOT NULL)")
        if store_path:
            self._import_legacy_json(store_path)

    def _import_legacy_json(self, store_path: Path) -> None:
        """One-time import of the old keystore.json beside the database. The file is kept, renamed."""
        legacy = store_path.with_name("keystore.json")
        if not legacy.exists() or self._db.execute("SELECT COUNT(*) FROM keys").fetchone()[0]:
            return
        data = json.loads(legacy.read_text())
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.executemany("INSERT OR IGNORE INTO keys VALUES (?,?)", list(data.items()))
            self._db.execute("COMMIT")
        legacy.rename(legacy.with_name("keystore.json.migrated"))
        os.chmod(legacy.with_name("keystore.json.migrated"), 0o600)

    # ---- construction ----
    @classmethod
    def from_env(cls, data_dir: Path) -> "Vault":
        data_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.get("GRIHA_MASTER_KEY")
        if env:
            key = base64.urlsafe_b64decode(env)
        else:
            kf = data_dir / "master.key"
            key = None
            for _ in range(100):                                     # several workers may start at once: one creates the file, the rest read it
                try:
                    fd = os.open(kf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    txt = kf.read_text().strip()
                    if txt:
                        key = base64.urlsafe_b64decode(txt)
                        break
                    time.sleep(0.05)                                 # the creator has not finished writing yet
                else:
                    key = os.urandom(32)
                    with os.fdopen(fd, "w") as f:
                        f.write(base64.urlsafe_b64encode(key).decode())
                        f.flush()
                        os.fsync(f.fileno())
                    break
            if key is None:
                raise RuntimeError("could not read or create the master key")
        return cls(key, data_dir / "keystore.db")

    @classmethod
    def ephemeral(cls) -> "Vault":
        return cls(os.urandom(32), None)

    # ---- internals ----
    def _row(self, subject: str):
        r = self._db.execute("SELECT wrapped FROM keys WHERE subject=?", (subject,)).fetchone()
        return r[0] if r else None

    def _dek(self, subject: str, create: bool) -> AESGCM:
        with self._lock:
            w = self._row(subject)
            if w is None:
                if not create:
                    raise ErasedError(subject)
                dek = os.urandom(32)
                nonce = os.urandom(12)
                mine = base64.b64encode(nonce + self._kek.encrypt(nonce, dek, subject.encode())).decode()
                self._db.execute("BEGIN IMMEDIATE")
                self._db.execute("INSERT OR IGNORE INTO keys VALUES (?,?)", (subject, mine))      # atomic: the first writer wins
                self._db.execute("COMMIT")
                w = self._row(subject)                                                            # use the winner's key, which may not be ours
        raw = base64.b64decode(w)
        return AESGCM(self._kek.decrypt(raw[:12], raw[12:], subject.encode()))

    # ---- public API ----
    def encrypt(self, subject: str, plaintext: bytes, aad: bytes = b"") -> str:
        nonce = os.urandom(12)
        ct = self._dek(subject, True).encrypt(nonce, plaintext, subject.encode() + b"|" + aad)
        return f"{VERSION}.{base64.urlsafe_b64encode(nonce + ct).decode()}"

    def decrypt(self, subject: str, token: str, aad: bytes = b"") -> bytes:
        ver, _, body = token.partition(".")
        if ver != VERSION:
            raise ValueError("unknown ciphertext version")
        raw = base64.urlsafe_b64decode(body)
        try:
            return self._dek(subject, False).decrypt(raw[:12], raw[12:], subject.encode() + b"|" + aad)
        except InvalidTag:
            raise ValueError("ciphertext failed authentication (tampered or wrong subject)")

    def erase(self, subject: str) -> bool:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            n = self._db.execute("DELETE FROM keys WHERE subject=?", (subject,)).rowcount
            self._db.execute("COMMIT")
        return n > 0

    def has(self, subject: str) -> bool:
        with self._lock:
            return self._row(subject) is not None

    def rewrap(self, new_master_key: bytes) -> int:
        """Rotate the master key: unwrap every DEK with the old key and wrap it with the new one, in one transaction."""
        new = AESGCM(new_master_key)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            rows = self._db.execute("SELECT subject, wrapped FROM keys").fetchall()
            out = []
            for subject, w in rows:
                raw = base64.b64decode(w)
                dek = self._kek.decrypt(raw[:12], raw[12:], subject.encode())
                nonce = os.urandom(12)
                out.append((base64.b64encode(nonce + new.encrypt(nonce, dek, subject.encode())).decode(), subject))
            self._db.executemany("UPDATE keys SET wrapped=? WHERE subject=?", out)
            self._db.execute("COMMIT")
            self._kek = new
        return len(out)
