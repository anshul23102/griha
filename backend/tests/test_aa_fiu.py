"""The Account Aggregator FIU protocol: detached JWS, key agreement and the Rahasya cipher, and a full consent-to-data flow against the mock Aggregator."""
import asyncio
import base64
import json

import pytest
from cryptography.exceptions import InvalidTag

from griha import aa, aa_fiu as f
from griha.aa_mock import MockAA


def test_detached_jws_covers_the_exact_body_bytes():
    key = f.new_rsa_key()
    body = b'{"a":1}'
    jws = f.sign_detached(body, key, "kid-1")
    assert jws.count(".") == 2 and jws.split(".")[1] == ""                                   # <header>..<signature>
    assert f.verify_detached(body, jws, {"kid-1": key.public_key()}) == "kid-1"
    for bad in (b'{"a":2}', b'{"a": 1}'):                                                    # a changed byte, even whitespace, breaks it
        with pytest.raises(f.SignatureError):
            f.verify_detached(bad, jws, {"kid-1": key.public_key()})
    with pytest.raises(f.SignatureError):
        f.verify_detached(body, jws, {"other": key.public_key()})                             # unknown key id
    h = json.loads(f.b64u_dec(jws.split(".")[0]))
    assert h == {"alg": "RS256", "kid": "kid-1", "b64": False, "crit": ["b64"]}


def test_both_sides_derive_the_same_key_and_tampering_is_detected():
    fiu_priv, fiu_nonce, fiu_km = f.new_key_material()
    fip_priv, fip_nonce, fip_km = f.new_key_material()
    ct = f.encrypt_fi(fip_priv, fiu_km, fip_nonce, b"balance 12345.67")
    assert f.decrypt_fi(fiu_priv, fip_km, fiu_nonce, ct) == b"balance 12345.67"
    raw = bytearray(base64.b64decode(ct)); raw[3] ^= 1
    with pytest.raises(InvalidTag):
        f.decrypt_fi(fiu_priv, fip_km, fiu_nonce, base64.b64encode(raw).decode())
    with pytest.raises(InvalidTag):                                                          # a different nonce gives a different key
        f.decrypt_fi(fiu_priv, fip_km, bytes(32), ct)
    key, iv = f._session(fiu_priv, fip_km["DHPublicKey"]["KeyValue"], fiu_nonce, base64.b64decode(fip_km["Nonce"]))
    assert len(key) == 32 and len(iv) == 12                                                  # AES-256 key, 96-bit GCM IV (XORed nonce bytes 20..32)


def _setup():
    fiu_key = f.new_rsa_key()
    kid = "fiu-test-key"
    aa_mock = MockAA({kid: fiu_key.public_key()})
    fiu = f.Fiu("GRIHA-FIU", fiu_key, kid, aa_mock.public, aa_mock.post, aa_mock.get)
    return fiu, aa_mock


def test_full_flow_consent_approval_encrypted_fetch_and_parse():
    async def run():
        fiu, mock = _setup()
        mock.profiles["9876543210@mock-aa"] = "Meena Patel"
        h = await fiu.request_consent("9876543210@mock-aa")
        assert (await fiu.consent_status(h["ConsentHandle"]))["ConsentStatus"]["status"] == "PENDING"
        mock.decide(h["ConsentHandle"], True)
        doc = await fiu.fetch_data(h["ConsentHandle"])
        ext = aa.parse_fi(json.dumps(doc).encode(), applicant_name="Meena Patel")
        assert ext.method == "account_aggregator" and len(ext.txns) > 100 and not [i for i in ext.issues if i.severity == "high"]
        assert any("decrypted" == t["step"] for t in fiu.trace)
        with pytest.raises(PermissionError):                                                    # a one-time consent cannot be used twice
            await fiu.fetch_data(h["ConsentHandle"])
    asyncio.run(run())


def test_rejected_consent_unsigned_and_foreign_requests_are_refused():
    async def run():
        fiu, mock = _setup()
        h = await fiu.request_consent("9000000000@mock-aa")
        mock.decide(h["ConsentHandle"], False)
        with pytest.raises(ValueError, match="rejected"):
            await fiu.fetch_data(h["ConsentHandle"])
        stranger = f.Fiu("EVIL-FIU", f.new_rsa_key(), "fiu-test-key", mock.public, mock.post, mock.get)     # signs with a key the AA does not know under that kid
        with pytest.raises(PermissionError, match="signature"):
            await stranger.request_consent("9000000000@mock-aa")
        raw = json.dumps(f.consent_request("x@mock-aa", "GRIHA-FIU")).encode()
        with pytest.raises(PermissionError):
            await mock.post("/Consent", raw, {"x-jws-signature": ""})                            # no signature at all
        # a consent artefact altered in transit fails verification at the FIU
        h2 = await fiu.request_consent("9000000001@mock-aa"); mock.decide(h2["ConsentHandle"], True)
        cid = (await fiu.consent_status(h2["ConsentHandle"]))["ConsentStatus"]["id"]
        art = (await fiu.get_artefact(cid) if hasattr(fiu, "get_artefact") else await mock.get(f"/Consent/{cid}"))["signedConsent"]
        hdr, pl, sig = art.split(".")
        forged = json.loads(f.b64u_dec(pl)); forged["Purpose"]["code"] = "999"
        with pytest.raises(f.SignatureError):
            f.verify_compact(f"{hdr}.{f.b64u(json.dumps(forged).encode())}.{sig}", mock.public)
    asyncio.run(run())


def test_aa_endpoints_run_the_whole_consent_flow_and_feed_the_document_store():
    from griha.api import app
    from tests.keyed import KeyedClient
    with KeyedClient(app) as c:
        r = c.post("/api/aa/consent", json={"phone": "9812345678", "name": "Priya Nair"}).json()
        assert r["status"] == "PENDING" and r["consent"]["purpose"].startswith("Loan underwriting") and r["trace"][0]["step"].startswith("POST /Consent")
        h = r["handle"]
        assert c.post(f"/api/aa/fetch/{h}").status_code == 409                                  # nothing can be fetched before the customer approves
        assert c.post(f"/api/aa/consent/{h}/decide", json={"approve": True}).json()["status"] == "ACTIVE"
        d = c.post(f"/api/aa/fetch/{h}")
        assert d.status_code == 200, d.text
        j = d.json()
        assert j["method"] == "account_aggregator" and j["transactions"] > 100 and j["holder_name"] == "Priya Nair" and [t["step"] for t in j["trace"]][-1] == "decrypted"
        assert c.post(f"/api/aa/fetch/{h}").status_code == 409                                  # one-time consent
        assert c.post("/api/aa/consent", json={"phone": "12345", "name": "X"}).status_code == 422
