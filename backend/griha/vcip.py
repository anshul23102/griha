"""Video-based Customer Identification Process (V-CIP): the procedure and the checks, from NBFC KYC Directions 2025 paras 26 and 27 (read in the primary text).

What is built: the SOP as enforced code. A session is run by a trained official; each session gets a freshly randomised set of liveness and profile questions (27(2)(iii));
completion is refused unless every mandatory element is on record, with the paragraph for each: live geo-tag and time stamp (27(1)(iv)), the identification information obtained
by one of the four permitted routes (27(2)(vi)), Aadhaar XML/QR or CKYCR download not older than three working days (27(2)(viii), (ix)), the PAN image unless an e-PAN was given
(27(2)(xi)), the customer's economic and financial profile confirmed (27(2)(x)), the current address captured if it differs from the OVD (27(2)(x)), a live liveness result, and no
prompting at the customer's end, which forces rejection (27(2)(iv)). A dropped call means a fresh session, never a resumed one (27(2)(ii)). Aadhaar number redaction is a fixed
property of what we store (27(2)(vii)): only SHA-256 hashes of the captured images are kept here.

What is NOT built: the video itself. Recording, storing and encrypting live audio-video, the liveness-detection model, the lender's own V-CIP infrastructure and the audit and
penetration tests of 27(1) are the lender's. The demo runs the customer and the official in one browser, which a real V-CIP never does.
"""
from __future__ import annotations

import secrets
from datetime import date, timedelta

IDENT_ROUTES = {"aadhaar_otp": "OTP-based Aadhaar e-KYC authentication", "aadhaar_offline": "Offline verification of Aadhaar (XML or Secure QR code)",
                "ckycr": "KYC records downloaded from CKYCR", "digilocker_ovd": "Equivalent e-document of an OVD, including DigiLocker"}
TIME_LIMITED = {"aadhaar_offline", "ckycr", "digilocker_ovd", "aadhaar_otp"}      # 27(2)(viii), (ix): the information must be at most three working days old

QUESTION_BANK = [
    ("LIVE-1", "liveness", "Please turn your head slowly to the left, then to the right."),
    ("LIVE-2", "liveness", "Hold up today's newspaper or a handwritten note with today's date next to your face."),
    ("LIVE-3", "liveness", "Blink twice and then read out the number I am about to show on screen."),
    ("LIVE-4", "liveness", "Move your phone to show the room you are sitting in, slowly, all the way round."),
    ("LIVE-5", "liveness", "Cover your left eye with your hand for three seconds."),
    ("PROF-1", "profile", "What is your employer's name, and how long have you worked there?"),
    ("PROF-2", "profile", "What is your monthly take-home income, roughly?"),
    ("PROF-3", "profile", "Which bank account will your instalments be paid from?"),
    ("PROF-4", "profile", "What is the purpose of this loan?"),
    ("PROF-5", "profile", "Is the address on your documents where you live now? If not, where?"),
    ("ID-1", "identity", "Please show your PAN card clearly to the camera (not needed if you gave an e-PAN)."),
    ("ID-2", "identity", "Please say your full name and your date of birth aloud."),
]


def new_questions(n: int = 6) -> list[dict]:
    """A fresh random selection in a fresh random order, always with at least one liveness, one profile and one identity question (27(2)(iii))."""
    rng = secrets.SystemRandom()
    pick = [rng.choice([q for q in QUESTION_BANK if q[1] == k]) for k in ("liveness", "profile", "identity")]
    rest = [q for q in QUESTION_BANK if q not in pick]
    rng.shuffle(rest)
    chosen = pick + rest[: max(0, n - 3)]
    rng.shuffle(chosen)
    return [{"id": q[0], "kind": q[1], "text": q[2]} for q in chosen]


def working_days_between(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def evaluate(s: dict, on: date) -> dict:
    """The decision for a finished session: passed, failed with reasons, or MUST BE REJECTED (prompting). Every reason cites its paragraph."""
    fail: list[dict] = []
    add = lambda rule, text, cite: fail.append({"rule": rule, "text": text, "cite": cite})                  # noqa: E731
    if s.get("disruption") == "dropped":
        add("DROPPED", "The call dropped. A fresh session must be started; this one cannot be resumed.", "KYC Directions 2025 para 27(2)(ii)")
    geo = s.get("geo") or {}
    if not (isinstance(geo.get("lat"), (int, float)) and isinstance(geo.get("lon"), (int, float)) and -90 <= geo["lat"] <= 90 and -180 <= geo["lon"] <= 180):
        add("GEO", "The live GPS co-ordinates of the customer were not captured.", "para 27(1)(iv)")
    if s.get("identification_method") not in IDENT_ROUTES:
        add("IDENT", "The identification information was not obtained by one of the four permitted routes.", "para 27(2)(vi)")
    elif s.get("id_obtained_on"):
        age = working_days_between(date.fromisoformat(s["id_obtained_on"]), on)
        if age > 3:
            add("STALE", f"The identification information is {age} working days old; it must be at most three.", "paras 27(2)(viii), (ix)")
    else:
        add("IDENT_DATE", "The date the identification information was obtained is missing.", "paras 27(2)(viii), (ix)")
    if not (s.get("photo_sha256") and len(s["photo_sha256"]) == 64):
        add("PHOTO", "A photograph of the customer present for identification was not captured.", "para 27(2)(vi)")
    if not (s.get("epan") or (s.get("pan_image_sha256") and len(s["pan_image_sha256"]) == 64)):
        add("PAN", "No clear image of the PAN card, and no e-PAN, was captured.", "para 27(2)(xi)")
    if not s.get("financial_profile_confirmed"):
        add("PROFILE", "The customer's economic and financial profile was not confirmed with the customer undertaking the V-CIP.", "para 27(2)(x)")
    if s.get("address_differs") and not s.get("current_address_recorded"):
        add("ADDRESS", "The current address differs from the OVD and was not recorded.", "para 27(2)(x)")
    if not s.get("liveness_passed"):
        add("LIVENESS", "The liveness check did not pass. (It must not exclude persons with special needs: use an alternative the SOP provides.)", "para 27(2)(i)")
    answered = {a.get("id") for a in s.get("answers", []) if a.get("ok") is not None}
    missing = [q["id"] for q in s.get("questions", []) if q["id"] not in answered and not (q["id"] == "ID-1" and s.get("epan"))]   # ID-1 asks for the PAN card: not needed when an e-PAN was given
    if missing:
        add("QUESTIONS", "Not every question of this session was asked and recorded: " + ", ".join(missing), "para 27(2)(iii)")
    if s.get("negative_list_hit"):
        add("NEGATIVE_LIST", "The name appears on a negative list: the case must go to the compliance officer, not be completed here.", "para 27(2)(v)")
    must_reject = bool(s.get("prompting_observed"))
    if must_reject:
        add("PROMPTING", "Prompting was observed at the customer's end: the account opening process must be rejected.", "para 27(2)(iv)")
    return {"passed": not fail, "must_reject": must_reject, "reasons": fail}
