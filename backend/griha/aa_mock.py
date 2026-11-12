"""A mock Account Aggregator (AA) with a mock bank (FIP) behind it, for testing the FIU in griha/aa_fiu.py end to end, in process.

It is the OTHER half of the protocol, written by us from the same public documentation: it verifies the FIU's detached JWS, issues a consent handle, lets the "customer" approve
or reject, signs the consent artefact, checks the FI request against the consent, and returns the FI data encrypted for the FIU with the Rahasya scheme. The data is synthetic.
It is not an Aggregator: no RBI licence, no real customers, no real bank. Its only claim is that the two halves agree.
"""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone

from . import aa, aa_fiu as f
from .synth import make_case

AA_KID = "mock-aa-" + uuid.uuid4().hex[:8]
MAX_STATE = 500


class MockAA:
    def __init__(self, fiu_keys: dict):
        self.key = f.new_rsa_key()
        self.fiu_keys = fiu_keys                       # kid -> RSA public key of each registered FIU
        self.consents: dict[str, dict] = {}            # handle -> state
        self.sessions: dict[str, dict] = {}
        self.profiles: dict[str, str] = {}             # customer VUA -> holder name (a test hook, not part of the protocol)

    @property
    def public(self):
        return self.key.public_key()

    def _trim(self, d: dict) -> None:
        while len(d) > MAX_STATE:
            d.pop(next(iter(d)))

    # ---- the AA's HTTP surface, as functions taking raw bytes so the signature covers exactly what was sent
    async def post(self, path: str, raw: bytes, headers: dict) -> dict:
        try:
            f.verify_detached(raw, headers.get("x-jws-signature", ""), self.fiu_keys)
        except f.SignatureError as e:
            raise PermissionError(f"401 {e}")
        body = json.loads(raw)
        if path == "/Consent":
            d = body["ConsentDetail"]
            if d["consentMode"] not in ("VIEW", "STORE", "QUERY", "STREAM") or d["fiTypes"] != ["DEPOSIT"]:
                raise ValueError("400 unsupported consent detail")
            handle = str(uuid.uuid4())
            self.consents[handle] = {"detail": d, "status": "PENDING", "id": None, "customer": d["Customer"]["id"], "txnid": body["txnid"]}
            self._trim(self.consents)
            return {"ver": "2.0.0", "timestamp": f.now(), "txnid": body["txnid"], "Customer": {"id": d["Customer"]["id"]}, "ConsentHandle": handle}
        if path == "/FI/request":
            cid = body["Consent"]["id"]
            c = next((x for x in self.consents.values() if x["id"] == cid), None)
            if not c or c["status"] != "ACTIVE":
                raise PermissionError("403 consent is not active")
            if body["Consent"]["digitalSignature"] != c["artefact"].split(".")[2]:
                raise PermissionError("403 consent signature does not match the artefact")
            now = datetime.now(timezone.utc)
            if datetime.fromisoformat(c["detail"]["consentExpiry"].replace("Z", "+00:00")) < now:
                raise PermissionError("403 consent has expired")
            if body["FIDataRange"]["from"] < c["detail"]["FIDataRange"]["from"] or body["FIDataRange"]["to"] > c["detail"]["FIDataRange"]["to"]:
                raise PermissionError("403 requested range is outside the consent")
            if c.get("fetched"):
                raise PermissionError("403 a one-time consent can be used once")
            c["fetched"] = True
            sid = str(uuid.uuid4())
            self.sessions[sid] = {"consent": c, "km": body["KeyMaterial"]}
            self._trim(self.sessions)
            return {"ver": "2.0.0", "timestamp": f.now(), "txnid": body["txnid"], "consentId": cid, "sessionId": sid}
        raise ValueError("404 unknown path")

    async def get(self, path: str) -> dict:
        parts = path.strip("/").split("/")
        if parts[:2] == ["Consent", "handle"]:
            c = self.consents[parts[2]]
            return {"ver": "2.0.0", "timestamp": f.now(), "txnid": c["txnid"], "ConsentHandle": parts[2], "ConsentStatus": {"id": c["id"], "status": c["status"]}}
        if parts[0] == "Consent":
            c = next(x for x in self.consents.values() if x["id"] == parts[1])
            return {"ver": "2.0.0", "timestamp": f.now(), "txnid": c["txnid"], "ConsentId": parts[1], "status": c["status"], "signedConsent": c["artefact"]}
        if parts[:2] == ["FI", "fetch"]:
            s = self.sessions[parts[2]]
            c = s["consent"]
            name = self.profiles.get(c["customer"], "Account Holder")
            seed = int(hashlib.sha256(c["customer"].encode()).hexdigest()[:8], 16) % 100_000
            app, _ = make_case(seed)
            app.applicant.name = name
            plain = aa.to_fi(app)                                         # the mock bank's DEPOSIT FI document for this customer
            priv, nonce, km = f.new_key_material()
            enc = f.encrypt_fi(priv, s["km"], nonce, plain)
            return {"ver": "2.0.0", "timestamp": f.now(), "txnid": c["txnid"], "FI": [{"fipID": "MOCK-BANK-FIP", "data": [{"linkRefNumber": str(uuid.uuid4()),
                    "maskedAccNumber": "XXXXXX" + seed.__str__()[-4:].zfill(4), "encryptedFI": enc}], "KeyMaterial": km}]}
        raise ValueError("404 unknown path")

    # ---- the customer's side: the AA app where a person approves or rejects (not part of the FIU-facing API)
    def decide(self, handle: str, approve: bool) -> dict:
        c = self.consents[handle]
        if c["status"] != "PENDING":
            raise ValueError("consent already decided")
        if not approve:
            c["status"] = "REJECTED"
            return {"status": "REJECTED"}
        c["id"] = str(uuid.uuid4())
        c["status"] = "ACTIVE"
        d = c["detail"]
        c["artefact"] = f.sign_compact({"consentId": c["id"], "iss": "mock-aa", "iat": f.now(), **d}, self.key, AA_KID)
        return {"status": "ACTIVE", "consentId": c["id"]}
