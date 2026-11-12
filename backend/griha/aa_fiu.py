"""The Financial Information User (FIU) side of the Account Aggregator protocol, with an in-process mock Aggregator to test it against.

What is implemented, and from what:
* Request signing: every FIU-to-AA call carries `x-jws-signature`, a detached JWS (RFC 7515 Appendix F, unencoded payload as in RFC 7797): header
  {"alg":"RS256","kid":...,"b64":false,"crit":["b64"]}, form `<header>..<signature>`, signed over the exact bytes of the HTTP body. (As described in the public FinVu
  ReBIT JWS note.) The consent artefact the AA returns is an ordinary compact JWS that the FIU verifies.
* Messages: consent request (`ConsentDetail`), consent handle and status, consent artefact, FI data request (`Consent`, `KeyMaterial`), FI fetch, following the ReBIT
  AA API as documented publicly by Sahamati and integrators.
* Encryption of the FI data in transit, exactly as in Sahamati's open-source reference implementation (Rahasya, ecdh_build/XCipherService.java): X25519 key agreement; the
  two 32-byte nonces are XORed; HKDF-SHA256 with the first 20 bytes of the XOR as salt and no info gives a 32-byte AES key; the last 12 bytes of the XOR are the GCM IV;
  AES-256-GCM with a 16-byte tag; ciphertext and keys base64. Public keys travel as X.509 SubjectPublicKeyInfo DER (raw 32-byte keys are also accepted).

What this is NOT: a registered FIU, a certified integration or a connection to a real Account Aggregator. Becoming an FIU needs RBI-regulated entity status and onboarding with
an AA and Sahamati; the AA API pages were not reachable when this was written, so message shapes come from public integrator documentation and are unverified against the
current ReBIT specification. The mock Aggregator is our own code on the other end of the same protocol: it proves the two halves agree, not that a real AA will accept them.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ------------------------------------------------------------------ signatures
class SignatureError(ValueError):
    pass


def new_rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def sign_detached(body: bytes, key: rsa.RSAPrivateKey, kid: str) -> str:
    header = b64u(json.dumps({"alg": "RS256", "kid": kid, "b64": False, "crit": ["b64"]}, separators=(",", ":")).encode())
    sig = key.sign(header.encode() + b"." + body, padding.PKCS1v15(), hashes.SHA256())
    return f"{header}..{b64u(sig)}"


def verify_detached(body: bytes, jws: str, keys: dict[str, rsa.RSAPublicKey]) -> str:
    """Verify against the RAW body bytes as received. Returns the kid. Raises SignatureError on anything wrong."""
    try:
        h, mid, s = jws.split(".")
        header = json.loads(b64u_dec(h))
    except Exception:
        raise SignatureError("malformed signature header")
    if mid or header.get("alg") != "RS256" or header.get("b64") is not False or header.get("crit") != ["b64"]:
        raise SignatureError("not a detached RS256 JWS with an unencoded payload")
    pub = keys.get(header.get("kid", ""))
    if not pub:
        raise SignatureError("unknown key id")
    try:
        pub.verify(b64u_dec(s), h.encode() + b"." + body, padding.PKCS1v15(), hashes.SHA256())
    except InvalidSignature:
        raise SignatureError("signature does not match the body")
    return header["kid"]


def sign_compact(payload: dict, key: rsa.RSAPrivateKey, kid: str) -> str:
    h = b64u(json.dumps({"alg": "RS256", "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode())
    p = b64u(json.dumps(payload, separators=(",", ":")).encode())
    return f"{h}.{p}.{b64u(key.sign(f'{h}.{p}'.encode(), padding.PKCS1v15(), hashes.SHA256()))}"


def verify_compact(token: str, pub: rsa.RSAPublicKey) -> dict:
    try:
        h, p, s = token.split(".")
        pub.verify(b64u_dec(s), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())
        return json.loads(b64u_dec(p))
    except (InvalidSignature, ValueError):
        raise SignatureError("consent artefact signature is not valid")


# ------------------------------------------------------------------ key material and the FI data cipher (Sahamati Rahasya scheme)
def new_key_material(minutes: int = 30) -> tuple[x25519.X25519PrivateKey, bytes, dict]:
    priv = x25519.X25519PrivateKey.generate()
    nonce = os.urandom(32)
    der = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    km = {"cryptoAlg": "ECDHE", "curve": "Curve25519", "params": "cipher=AES/GCM/NoPadding;KEY_DERIVATION_FUNCTION=HKDF;hash=SHA256",
          "DHPublicKey": {"expiry": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "Parameters": "", "KeyValue": base64.b64encode(der).decode()},
          "Nonce": base64.b64encode(nonce).decode()}
    return priv, nonce, km


def _load_public(key_value: str) -> x25519.X25519PublicKey:
    raw = base64.b64decode(key_value)
    return x25519.X25519PublicKey.from_public_bytes(raw) if len(raw) == 32 else serialization.load_der_public_key(raw)   # type: ignore[return-value]


def _session(priv: x25519.X25519PrivateKey, remote_pub_b64: str, nonce_a: bytes, nonce_b: bytes) -> tuple[bytes, bytes]:
    if len(nonce_a) != 32 or len(nonce_b) != 32:
        raise ValueError("nonces must be 32 bytes")
    shared = priv.exchange(_load_public(remote_pub_b64))
    x = bytes(a ^ b for a, b in zip(nonce_a, nonce_b))
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=x[:20], info=None).derive(shared)
    return key, x[20:32]                                   # AES key, GCM IV


def encrypt_fi(priv: x25519.X25519PrivateKey, remote_km: dict, own_nonce: bytes, plaintext: bytes) -> str:
    key, iv = _session(priv, remote_km["DHPublicKey"]["KeyValue"], own_nonce, base64.b64decode(remote_km["Nonce"]))
    return base64.b64encode(AESGCM(key).encrypt(iv, plaintext, None)).decode()


def decrypt_fi(priv: x25519.X25519PrivateKey, remote_km: dict, own_nonce: bytes, encrypted_b64: str) -> bytes:
    key, iv = _session(priv, remote_km["DHPublicKey"]["KeyValue"], own_nonce, base64.b64decode(remote_km["Nonce"]))
    return AESGCM(key).decrypt(iv, base64.b64decode(encrypted_b64), None)       # raises InvalidTag if anything differs


# ------------------------------------------------------------------ messages
def consent_request(customer_vua: str, fiu_id: str, *, days_valid: int = 1, history_months: int = 12) -> dict:
    t = datetime.now(timezone.utc)
    return {"ver": "2.0.0", "timestamp": now(), "txnid": str(uuid.uuid4()), "ConsentDetail": {
        "consentStart": now(), "consentExpiry": (t + timedelta(days=days_valid)).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "consentMode": "VIEW", "fetchType": "ONETIME",
        "consentTypes": ["TRANSACTIONS", "SUMMARY", "PROFILE"], "fiTypes": ["DEPOSIT"], "DataConsumer": {"id": fiu_id}, "DataProvider": {"id": ""}, "Customer": {"id": customer_vua},
        "Purpose": {"code": "102", "refUri": "https://api.rebit.org.in/aa/purpose/102.xml", "text": "Loan underwriting: verify income and obligations for a home-loan application",
                    "Category": {"type": "Loan"}},
        "FIDataRange": {"from": (t - timedelta(days=30 * history_months)).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "to": now()},
        "DataLife": {"unit": "MONTH", "value": 0}, "Frequency": {"unit": "MONTH", "value": 1}}}


def fi_request(consent_id: str, digital_signature: str, fi_range: dict, km: dict) -> dict:
    return {"ver": "2.0.0", "timestamp": now(), "txnid": str(uuid.uuid4()), "FIDataRange": fi_range, "Consent": {"id": consent_id, "digitalSignature": digital_signature}, "KeyMaterial": km}


class Fiu:
    """The FIU. `post` and `get` are async callables (an HTTP client, or the mock Aggregator in process): post(path, body_bytes, headers) -> dict."""

    def __init__(self, fiu_id: str, key: rsa.RSAPrivateKey, kid: str, aa_public: rsa.RSAPublicKey, post, get):
        self.fiu_id, self.key, self.kid, self.aa_public, self._post, self._get = fiu_id, key, kid, aa_public, post, get
        self.trace: list[dict] = []

    def _t(self, step: str, detail: str) -> None:
        self.trace.append({"step": step, "detail": detail})

    async def _signed_post(self, path: str, body: dict) -> dict:
        raw = json.dumps(body, separators=(",", ":")).encode()
        self._t(f"POST {path}", f"body {len(raw)} bytes, x-jws-signature (detached RS256, kid {self.kid[:8]}…)")
        return await self._post(path, raw, {"x-jws-signature": sign_detached(raw, self.key, self.kid), "content-type": "application/json"})

    async def request_consent(self, customer_vua: str) -> dict:
        r = await self._signed_post("/Consent", consent_request(customer_vua, self.fiu_id))
        self._t("consent handle issued", r["ConsentHandle"][:8] + "…")
        return r

    async def consent_status(self, handle: str) -> dict:
        return await self._get(f"/Consent/handle/{handle}")

    async def fetch_data(self, handle: str) -> dict:
        """Consent approved -> fetch the signed artefact, verify it, request the FI data with fresh key material, fetch it, decrypt it. Returns the FI document (JSON)."""
        st = await self.consent_status(handle)
        if st["ConsentStatus"]["status"] != "ACTIVE":
            raise ValueError("consent is " + st["ConsentStatus"]["status"].lower())
        cid = st["ConsentStatus"]["id"]
        art = await self._get(f"/Consent/{cid}")
        claims = verify_compact(art["signedConsent"], self.aa_public)
        self._t("consent artefact verified", f"signed by the Aggregator; purpose {claims['Purpose']['code']}, expires {claims['consentExpiry'][:10]}")
        priv, nonce, km = new_key_material()
        self._t("key material", "fresh X25519 key pair and 32-byte nonce for this fetch only")
        resp = await self._signed_post("/FI/request", fi_request(cid, art["signedConsent"].split(".")[2], claims["FIDataRange"], km))
        fetched = await self._get(f"/FI/fetch/{resp['sessionId']}")
        item = fetched["FI"][0]
        self._t("encrypted FI received", f"{len(item['data'][0]['encryptedFI'])} base64 characters from FIP {item['fipID']}")
        plain = decrypt_fi(priv, item["KeyMaterial"], nonce, item["data"][0]["encryptedFI"])
        self._t("decrypted", f"ECDH + XOR of nonces + HKDF-SHA256 + AES-256-GCM: {len(plain)} bytes of DEPOSIT FI")
        return json.loads(plain)
