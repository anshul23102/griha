"""Online backup of the audit log and key store (DPDP Rules 2025 rule 6(1)(d), (e): backups, and logs kept for at least a year).

    python -m griha.backup [--data-dir DIR] [--dest DIR] [--keep N]

Uses SQLite's backup API, so it is safe while the server is writing. The copy is opened read-only afterwards and its audit hash chain is verified.
master.key is deliberately NOT copied: wrapped case keys stored beside the key that unwraps them would defeat the encryption. Keep master.key in a separate,
access-controlled place (a cloud KMS in production).
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import time
from pathlib import Path

from .audit import AuditLog

FILES = ("audit.db", "keystore.db")


def backup(data_dir: Path, dest_root: Path, keep: int = 14) -> Path:
    dest_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(dest_root, 0o700)
    now = time.time()
    dest = dest_root / (time.strftime("%Y%m%dT%H%M%S", time.gmtime(now)) + f"-{int(now * 1000) % 1000:03d}")
    dest.mkdir(mode=0o700)
    for name in FILES:
        src = data_dir / name
        if not src.exists():
            continue
        a = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        b = sqlite3.connect(dest / name)
        try:
            a.backup(b)
        finally:
            b.close()
            a.close()
        os.chmod(dest / name, 0o600)
    if (dest / "audit.db").exists():
        res = AuditLog(dest / "audit.db").verify()
        if not res["ok"]:
            raise RuntimeError(f"backup failed verification: chain broken at {res['broken_at']}")
    olds = sorted(p for p in dest_root.iterdir() if p.is_dir())[:-keep] if keep > 0 else []
    for p in olds:
        for f in p.iterdir():
            f.unlink()
        p.rmdir()
    return dest


def main() -> None:
    from . import config
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    ap.add_argument("--dest", type=Path, default=None)
    ap.add_argument("--keep", type=int, default=14)
    a = ap.parse_args()
    d = backup(a.data_dir, a.dest or a.data_dir.parent / "griha-backups", a.keep)
    print(f"backup written to {d}; audit chain verified; master.key not included")


if __name__ == "__main__":
    main()
