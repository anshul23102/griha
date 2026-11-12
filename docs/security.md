# Griha security and privacy

All applicants shown anywhere in this project are synthetic. The controls below are written for real personal and financial data.

## What is protected, and how

| Asset | Control | Where |
|---|---|---|
| Applicant data at rest | AES-256-GCM envelope encryption. One random data key per case, wrapped by a master key. The audit log stores only ciphertext | `crypto.py`, `engine.py` |
| Applicant data inside the workflow engine | Everything crossing Temporal (case, stage results, decision, officer review) is sealed under the case key with a purpose tag (AAD). Temporal history shows ciphertext and flags only | `engine.seal/unseal`, `activities.py` |
| Right to erasure (DPDP Act) | Crypto-shredding: destroying the case key makes the stored input and the Temporal history unreadable; the hash chain still verifies. Where the KYC Directions require records to be kept (5 years, para 47), a request is logged as ERASURE_DEFERRED and refused until that date | `crypto.py`, `POST /api/cases/{id}/erase` (admin, reason required) |
| Data-principal requests | Withdraw consent, access, correct, erase: logged in the audit chain with a 90-day response date; withdrawing consent stops all further processing of the case. No free text is stored | `POST /api/cases/{id}/rights` |
| What the applicant can see | Fraud findings, sanctions matches, STR signals, the customer risk category and officers' notes are removed from the applicant's view; staff see all | `redact.py` |
| Backups | Online SQLite backup of audit log and key store, hash chain verified on the copy, files 0600, master key deliberately excluded | `python -m griha.backup` |
| A case's contents | Capability access. The creator gets a 128-bit key (HMAC of the case ID under a server secret); every case endpoint needs that key or a staff login. A missing or wrong key returns the same 404 as a case that does not exist. Public statistics carry no case IDs | `auth.case_access` |
| Shared applicant link | The key travels in the URL fragment (`#k=`), which browsers never send to servers, and is removed from the address bar once stored in the tab's `sessionStorage` | `frontend/src/api.ts` |
| Staff sessions | HMAC-signed tokens, 8 h expiry, unique id, server-side revocation on logout | `auth.py` |
| Passwords | PBKDF2-HMAC-SHA256, 600,000 rounds, random per-user salt; constant work for unknown accounts; 5 failures lock the account for 5 minutes, on top of a per-IP rate limit | `auth.py` |
| Roles | underwriter and admin; four-eyes rule: only admin may approve a fraud-flagged referral; erase and tamper demo are admin only | `api.py` |
| Tamper evidence | Hash-chained audit log, byte-for-byte replay of any decision, admin tamper demo that works on a copy | `audit.py` |
| Input handling | Strict Pydantic bounds on every field; control and bidirectional-override characters refused; validation errors never echo the rejected input (and no longer crash on Infinity); PDF uploads checked by magic bytes, size and page limits, prompt-injection scan | `intake.py`, `api.py`, `docextract.py` |
| Uploaded statements | Held in memory only, 30-minute expiry, 200 maximum, 128-bit identifiers | `api.py` |
| Files on disk | Data directory mode 0700; audit log, key store, master key and session key mode 0600 | `audit.py`, `crypto.py`, `auth.py` |
| Transport and browser | Security headers on every response (nosniff, frame deny, no referrer, no-store, strict CSP for the API, HSTS, CORP, permissions policy); production frontend served with a strict CSP (hash-pinned theme script, no inline script, no eval) | `api.py`, `frontend/vite.config.ts` |
| Dependencies | `pnpm audit --prod` and `pip-audit` report no known vulnerabilities (checked 2026-11-10) | |
| Rate limiting | Per-IP, configurable; health and Prometheus scrape exempt | `api.py` |

Tests: `backend/tests/test_security.py`, `test_crypto.py`, `test_persistence.py`, and the browser test "privacy".

## Honest limits

- The master key lives in the data directory (or `GRIHA_MASTER_KEY`). In production it belongs in a KMS or HSM; the vault is built so that swap changes one function.
- Demo users share one password and are shown on the login screen. Production would use the lender's SSO and MFA. The password is set by `GRIHA_DEMO_PASSWORD`.
- TLS is not terminated by the app. Put it behind a TLS-terminating proxy; the HSTS header is already sent.
- Staff tokens are held in `localStorage` for convenience. The production CSP limits script injection; an HttpOnly cookie session would be the next step.
- The Temporal UI and Grafana run unauthenticated on localhost for the demo. Keep them off the public network or put them behind SSO.
- Case access keys are not rotated or revocable per case. Erasure is the revocation.
- Decisions in memory are not encrypted while the process runs.
- Third-party data feeds are simulated, so their own security is out of scope.
- Data residency: the RBI Digital Lending Directions 2025 (para 13(iv)) require borrower data to be stored only on servers in India. The hosted demo runs in a region outside India and holds only synthetic data; a real deployment must run in India.

## Regulatory duties, read in the primary text

Read in full: the NBFC Know Your Customer Directions 2025 (RBI/DOR/2025-26/361, updated 29 Dec 2025) and the Digital Personal Data Protection Rules 2025 (G.S.R. 846(E) with corrigendum 892(E) and commencement notification 843(E)). The files are kept on the developer's machine, not redistributed.

| Duty | Source | State |
|---|---|---|
| Rejection of an application needs application of mind, and an officer records the reason | KYC Directions para 18 | Built. A PAN failure or a screening match is referred to an officer instead of an automatic decline; the review needs a written reason of at least 15 characters |
| The decision on KYC compliance is not outsourced | para 13 | Built as routing: the engine flags, an officer decides |
| Aadhaar is voluntary | para 23, explanation 4 | Built. A missing e-KYC refers to an officer, who may accept another officially valid document |
| Customer risk category, suspicion and STR are not revealed to the customer | paras 19, 20(4), 52 | Built (`redact.py`), tested by `test_privacy_rules.py` |
| Online onboarding is non-face-to-face: rate the customer high-risk, enhanced checks | para 44 | Control EDD records the category. Address positive confirmation (44(3)) is for the lender |
| Keep identification and transaction records for five years | para 47 | Built as a retention hold on erasure. Off only where all data is synthetic (`GRIHA_RETENTION_HOLD=0`, set in the public demo) |
| No cross-selling or sharing of customer data without permission | para 61 | Consent wording and purpose limitation; no sharing exists |
| Screen names against sanctions lists | paras 54 to 56 | Built against four real lists: UN, OFAC, EU and UK, about 31,000 entries (`sanctions.py`, `--refresh` command). A match goes to an officer and is hidden from the applicant. Not built: OFAC/EU/UK/MHA lists, PEP data, daily re-screening of existing customers |
| V-CIP | paras 26 and 27 | The procedure is built as an enforced checklist (`vcip.py`): randomised questions, live geo-tag, identification at most three working days old, PAN image, financial profile, liveness, prompting forces rejection, a dropped call needs a fresh session. Not built: recording and storing the video, the liveness model, the lender's own V-CIP infrastructure and its audits |
| CKYCR upload in 10 days | para 63 | Not built. Needs a registered entity, CERSAI access and its specification, which is not public |
| Release of property documents; compensation for delay | RBC paras 35 to 41 | Built (`servicing.py`): 30-day clock (60 if lost or damaged), ₹5,000 a day, reason for delay recorded |
| Quarterly statement | RBC para 31(6) | Built, as an illustration (no loan is disbursed here) |
| Recovery agents: due diligence, notice, hours, conduct | RBC paras 93 to 101; HFC para 170 | Built as enforced rules with a public empanelment list; a contact outside 8:00 a.m. to 7:00 p.m., by an unlisted agent, to a relative, without a recording notice or beyond the daily limit is refused and the refusal is logged |
| Notice with itemised data, purpose, withdrawal, rights, complaint to the Board | DPDP rule 3 | Built (`/privacy`, Hindi and English) |
| Encryption or masking, access control, access logs, backups, one-year log retention | DPDP rule 6 | Built: per-case encryption, case keys and roles, hash-chained log, `griha.backup`. Retention length is the lender's to set |
| Breach notice to each person and to the Board within 72 hours | DPDP rule 7 | Built as a register: admin logs a breach, the 72-hour deadline is computed and shown overdue when missed, each of the three notices is marked off, all in the hash-chained log. It does not send the notices; a named person must |
| Retain data and logs at least one year, erase after | DPDP rule 8(3) | Partly: the audit log is append-only and the retention hold covers five years where KYC applies |
| Publish a contact person | DPDP rule 9 | The privacy page says the lender must name one |
| Rights requests answered within 90 days | DPDP rule 14(3) | Built: logged with a due date |
| Cross-border transfer | DPDP rule 15 with RBI Digital Lending Directions para 13(iv) | The hosted demo is outside India with synthetic data only. A real deployment must store data in India |

Commencement: DPDP rules 3 and 5 to 16 start 13 May 2027, rule 4 (consent managers) on 13 Nov 2026. We follow them now so that nothing changes at that date.
