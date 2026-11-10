"""Minimal HMAC-signed bearer tokens with PBKDF2-hashed demo users. Replace with the lender's SSO in production."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Header, HTTPException

from . import config


def _persistent_secret() -> bytes:
    """Signing secret. From GRIHA_SECRET if set, else a random 256-bit key kept in the data directory (0600) so that
    tokens and applicant case links survive an API restart."""
    env = os.environ.get("GRIHA_SECRET")
    if env:
        return env.encode()
    path = config.DATA_DIR / "session.key"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(100):                                     # several workers may start at once: one creates the file, the rest read it
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            txt = path.read_bytes().strip()
            if txt:
                return txt
            time.sleep(0.05)                                 # the creator has not finished writing yet
        else:
            key = secrets.token_hex(32).encode()
            with os.fdopen(fd, "wb") as f:
                f.write(key)
                f.flush()
                os.fsync(f.fileno())
            return key
    raise RuntimeError("could not read or create the session key")


SECRET = _persistent_secret()
_PBKDF2_ROUNDS = 600_000          # OWASP 2023 guidance for PBKDF2-HMAC-SHA256


def _hash(pw: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, _PBKDF2_ROUNDS).hex()


def case_key(case_id: str) -> str:
    """Capability key for one case, handed only to the person who created it. 128 bits, derived with HMAC so nothing is stored."""
    return hmac.new(SECRET, b"case-access:" + case_id.encode(), hashlib.sha256).hexdigest()[:32]


# Demo credentials are printed in the UI login hint. Override with GRIHA_DEMO_PASSWORD.
_DEMO_PW = os.environ.get("GRIHA_DEMO_PASSWORD", "griha-demo")


def _user(role: str, name: str) -> dict:
    salt = secrets.token_bytes(16)          # a fresh salt per user, so equal passwords never share a hash
    return {"role": role, "salt": salt, "pw": _hash(_DEMO_PW, salt), "name": name}


USERS = {"officer@griha.demo": _user("underwriter", "Credit Officer"), "admin@griha.demo": _user("admin", "Credit Head")}
_FAILS: dict[str, list[float]] = {}
LOCKOUT_AFTER, LOCKOUT_SECONDS = 5, 300
_DUMMY = {"salt": secrets.token_bytes(16)}
_DUMMY["pw"] = _hash(secrets.token_hex(8), _DUMMY["salt"])


def locked(email: str) -> int:
    """Seconds left on an account lockout (per account, on top of the per-IP rate limit)."""
    now = time.time()
    fails = [t for t in _FAILS.get(email.lower(), []) if now - t < LOCKOUT_SECONDS]
    _FAILS[email.lower()] = fails
    return int(LOCKOUT_SECONDS - (now - fails[0])) if len(fails) >= LOCKOUT_AFTER else 0


def login(email: str, password: str) -> dict | None:
    u = USERS.get(email.lower())
    ref = u or _DUMMY                         # same work for unknown accounts: no user enumeration by timing
    ok = hmac.compare_digest(ref["pw"], _hash(password, ref["salt"])) and u is not None
    if not ok:
        _FAILS.setdefault(email.lower(), []).append(time.time())
        return None
    _FAILS.pop(email.lower(), None)
    body = base64.urlsafe_b64encode(json.dumps({"sub": email, "role": u["role"], "exp": time.time() + 8 * 3600, "jti": secrets.token_hex(8)}).encode()).decode()
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return {"token": f"{body}.{sig}", "role": u["role"], "name": u["name"], "email": email}


REVOKED: set[str] = set()


def revoke(token: str) -> None:
    c = verify(token)
    if c and c.get("jti"):
        REVOKED.add(c["jti"])


def verify(token: str) -> dict | None:
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest(), sig):
            return None
        claims = json.loads(base64.urlsafe_b64decode(body))
        return claims if claims["exp"] > time.time() and claims.get("jti") not in REVOKED else None
    except Exception:
        return None


def require(*roles: str):
    def dep(authorization: str = Header(default="")) -> dict:
        claims = verify(authorization.removeprefix("Bearer ").strip()) if authorization else None
        if not claims or claims["role"] not in roles:
            raise HTTPException(401 if not claims else 403, "authentication required" if not claims else "insufficient role")
        return claims
    return dep


def case_access(case_id: str, authorization: str = Header(default=""), x_case_key: str = Header(default="")) -> str:
    """Staff with a valid bearer token, or the holder of this case's key. Anyone else gets a plain 404 (no existence oracle)."""
    claims = verify(authorization.removeprefix("Bearer ").strip()) if authorization else None
    if claims and claims["role"] in ("underwriter", "admin"):
        return "staff"
    if x_case_key and hmac.compare_digest(x_case_key, case_key(case_id)):
        return "applicant"
    raise HTTPException(404, "case not found")
