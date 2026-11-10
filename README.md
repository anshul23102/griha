# Griha: automated mortgage underwriting engine

Hero Housing Fintech Challenge, Problem Statement 2 (i-Hack, IIT Bombay E-Summit 2026).
Home Loan and Loan Against Property decisions in seconds: approve, reject or refer, with reasons an auditor can replay.

**All applicant data is synthetic. Model metrics describe a simulation, not real borrowers. No paid API or cloud service is used anywhere.**

![architecture](docs/architecture.svg)

## Run it

One command starts everything (Temporal, Prometheus, Grafana, the API with its Temporal worker, and the web app). All free and local.

```bash
cd backend && uv sync && uv run python -m griha.train 6000   # once: trains the models into artifacts/ (about 20 s)
```
```bash
ops/start.sh        # then open http://127.0.0.1:5173
ops/stop.sh
```
Tools needed once: `brew install temporal prometheus grafana`. Without Temporal the API falls back to the in-process engine and the Operations page says so.

| URL | What |
|---|---|
| http://127.0.0.1:5173 | the app |
| http://localhost:8233 | Temporal UI: every case's event history, retries, review timers |
| http://localhost:3000 | Grafana dashboard (anonymous viewer; admin / griha-demo) |
| http://localhost:9090 | Prometheus |

Officer logins: `officer@griha.demo`, `admin@griha.demo`, password `griha-demo` (demo only).

Tests: `cd backend && uv run pytest -q` (118 tests; the Temporal tests boot their own dev server) and `cd frontend && pnpm e2e` (23 browser tests, with accessibility checks, against the running stack).

Optional free local document reader: install [Ollama](https://ollama.com), `ollama pull qwen2.5:3b`. It is driven through a typed Pydantic AI agent. Without it, a deterministic text parser reads statements.

## What runs on what
- **Temporal** (durable workflows): `UnderwritingWorkflow` fetches the four data sources in parallel with retries, runs each stage as an activity, and exposes live progress as a query. `ReviewWorkflow` holds a referred case until the officer's decision arrives as an Update, with an SLA timer that escalates and audits.
- **Pydantic AI**: typed, validated, auto-retried extraction from statement text by a local model.
- **Prometheus + Grafana + Operations page**: decisions, stage latency, fraud flags, rule hits, retries, SLA escalations, model calls.

## The interface
Designed as "The Reservation Chart": Indian Railways station-board signage (bilingual Devanagari over Latin), ruled chart tables, a route strip of pipeline stations, and a thermal-ticket verdict. See `PRODUCT.md` (who and why) and `DESIGN.md` (tokens and rules).
- **Apply**: a real four-step form (applicant, loan, property, bank and consent). Every field goes to `POST /api/applications/new`. Bank, bureau, KYC and land records come from simulated adapters, deterministic per PAN, or you upload a statement PDF.
- **Case**: route strip, verdict ticket, reasons, Path to Yes (re-runs via `POST /api/cases/{id}/retry`), evidence folds, officer review, printable decision letter.
- **Lender desk**, **Policy simulator**, **Governance**: officer sign-in, case chart with keyboard navigation, portfolio replay, audit verify / replay / tamper demo / erasure, model card, regulatory map.
- **Home** is a product page: live demo of the real engine, how a decision is made, a "what can I borrow" calculator, FAQ and a two-minute guide.
- **PS2 checklist** maps all eight requirements and the six judging criteria to where they are shown, what was measured and the honest limit.
- Every case now shows data-source lineage, a document verification table, fifteen regulatory controls (eleven shown to the applicant), a risk scorecard and AML signals; Governance adds baselines, calibration by decile and a capacity benchmark.
- **Operations** page: orchestrator status, monitoring links, live engine numbers.
- English and Hindi (Hind throughout), night platform (default) and day platform themes.

## How each of the 8 PS2 requirements is covered

| # | Requirement | Where |
|---|---|---|
| 1 | Integrate data sources | `griha/models.py` input contract; data-integration stage with missing-source handling; PDF upload (`docextract.py`). Bureau, KYC and land records are simulated, shaped like the real feeds; the AA adapter parses the real ReBIT format |
| 2 | Eligibility and policy | `eligibility` stage (FOIR + LTV sizing, counter-offers) and `policy.py` + `policy/v1.yaml` (18 rules, hashed, full trace) |
| 3 | Fraud and KYC/AML | `fraud.py`: balance arithmetic, round-trips, window dressing, entity graph, anomaly model, name match, real screening against the UN Security Council Consolidated List (`sanctions.py`) |
| 4 | Risk scoring | `risk.py`: monotone-constrained LightGBM ensemble, isotonic calibration, native SHAP reasons, conformal sets |
| 5 | Documents and property | `docextract.py` (injection-safe), `property.py` (quantile GBM, comparables, circle rate, title flags) |
| 6 | Compliance checks | `policy/v1.yaml` `compliance:` section, shown in the Governance page with a verified / secondary / internal label per claim |
| 7 | Instant decisioning | `engine.py`: about 12 ms per case; approve / reject / refer with four refer queues, offer and Key Fact Statement |
| 8 | Explainability and governance | reasons on every decision, `audit.py` hash chain, replay, `crypto.py` encrypted vault and erasure, model card, human review with four-eyes rule |

## Beyond the brief
- **Path to Yes**: for non-approved cases, searches amount, tenure and co-applicant income for the smallest change that flips the outcome.
- **Policy impact simulator**: replay 1,000 stored applications under a changed threshold; see approval rate, expected loss and a fairness screen (per attribute, with a 95% interval so small-sample wobble is not read as bias) before shipping.
- **Crypto-shredding erasure**: reconciles an immutable audit log with the right to erasure.
- **Injection-safe document reading**: embedded instructions in a PDF are treated as evidence of tampering, never as commands.

## Measured results (synthetic data, held-out test set)
- Risk model: AUC about 0.74, KS about 0.38, predicted default 7.5% vs actual 6.0%. Deliberately modest: the synthetic world has noise.
- Property valuation: 80% of values within 10% of truth, MAPE 6.3%.
- Fraud (injected typologies): edited statements, window dressing, identity mismatch and rings were all flagged. Inflated declared income is flagged but not blocked, because decisions use income verified from the statement.
- Honest applicants: about 60% auto-approved, 32% referred, 8% declined. The refer rate is higher than a production target.
- Local LLM reader (qwen2.5:3b, M2 8 GB): 10 statement lines in 17 s and exact; 25 lines in 68 s with one line dropped. Too slow for full statements, so the text parser is the default and the LLM is an optional deep read with a cross-check.

## Evidence outside our own generator
Every figure above is on data this project generates. Two checks do not depend on it:
- **Real-data check** (`uv run python -m tools.validate_public`, results in `backend/artifacts/real_data_validation.json`, shown on the Governance page): the same recipe (monotone-constrained LightGBM + isotonic calibration) on two public datasets of real borrowers, 5-fold out-of-sample. German Credit (1,000 loans): AUC 0.788 monotone vs 0.793 unconstrained vs 0.782 logistic. Taiwan cards (30,000): 0.782 vs 0.783 vs 0.723 logistic. Mean calibration gap per decile 1.1% and 0.4%. Data: UCI Machine Learning Repository, CC BY 4.0. These are not Indian mortgages: they show the recipe works on real outcomes and that the monotone constraints cost almost no ranking power. They do not show accuracy on Indian home loans.
- **Real sanctions list**: names are screened against the UN Security Council Consolidated List (1,007 entries, snapshot 10 Nov 2026).

## What is real, simulated, and designed-for-not-built
| Real | Simulated (shaped like the real feed) | Designed for, not built |
|---|---|---|
| APR calculation (matches the RBI worked example), KFS in the RBC Annex I layout (English and Hindi), repo rate and RESIDEX figures, UN sanctions screen, ReBIT AA file parsing, audit chain, encryption and crypto-shredding, DPDP data-rights and breach register | Bureau, KYC, land records, Account Aggregator link, applicants, property price levels | AA consent flow and FIU signing, OFAC/EU/MHA lists, PEP data, CKYCR upload, V-CIP, address confirmation, quarterly borrower statements, document release, recovery-agent rules, Postgres, India-region hosting |

## Limits you should know
- No Indian loan-level data: model accuracy on Indian borrowers is unknown and the lender must retrain and validate on its own book. Property price levels are synthetic.
- The 90 / 80 / 75% LTV caps are in the RBI HFC Directions 2025 (para 58). FOIR, age, bureau and PD cut-offs are illustrative lender policy. The KFS, prepayment, KYC and data-protection rules were read in the primary texts (see below).
- The Hindi KFS and privacy notice were written for this prototype and have not been reviewed by a legal translator.
- The hosted demo runs in Sydney in one process on a small server; production data must stay in India (Digital Lending Directions para 13(iv)).
- Not a lending product. Not legal advice.

## Security and privacy

Case contents are private to the person who created them (capability key) and to staff; data is encrypted at rest and inside Temporal; erasure destroys the key. See [docs/security.md](docs/security.md) for the full control list, tests and honest limits.

## Model monitoring

`/api/ops` and the Operations page report Population Stability Index of live risk inputs against a reference population (each applicant counted once; readings start at 100 applicants). The same numbers are exported to Prometheus as `griha_feature_psi`. After a restart the case table is rebuilt from the encrypted audit log, so nothing is lost.

## Deploying

A single-container public demo on a small AWS server in its own project and a Cloudflare Tunnel for live sessions: see [docs/deploy.md](docs/deploy.md).

## Data sources

The Data sources page (`/sources`, `GET /api/sources`) lists every figure the product relies on with its publisher, date, link and honest status: real published figures (RBI repo rate 5.50% from the October 2026 MPC minutes, NHB RESIDEX Q3 FY2025-26), datasets identified but not yet used, synthetic data, our own assumptions, and sources we looked at and rejected. The base rate is derived from the repo rate (`config.py`), so a repo change moves quotes and the stress rate one for one. Real third-party datasets for validation go in `data-external/` and never leave your machine.

## Regulatory text and versions

The regulatory map (policy/v1.yaml, shown on Governance and per case) marks each row verified, secondary, internal or unverified. The RBI Digital Lending Directions 2025 were read in the primary text (applies to HFCs; KFS; cooling-off; grievance route with RBI escalation after 30 days; data stored only in India). The HFC Directions 2025 (Chapter X Fair Practices Code, Annexes IV and V), the NBFC KYC Directions, the NBFC Responsible Business Conduct Directions and the DPDP Rules were all read in the primary text. Every decision records the engine version; replay says plainly when the engine changed since a decision was made, so a changed digest is never mistaken for tampering.

## What the HFC Directions changed in the product

Reading the primary PDF turned up rules we had missed, now built: the KFS carries the para 131 disclosures (all-in cost, refund, penal and conversion charges, reset, 60-day exit if terms worsen; lender-set values are marked); a printable terms sheet follows the Annex IV layout (`/case/<id>/mitc`); the letter gives the NHB complaint route alongside the RBI one; and loans of Rs 50 lakh or more need two valuation reports (two independent from Rs 75 lakh) with the lower value used, otherwise the case goes to the property team (policy rule `VALUATION_REPORTS`; the Apply form takes the reports).

## Scale and storage

The audit log and the key vault are SQLite (WAL) with transactional, race-safe writes, so several worker processes share one database; cases are a projection of it. Measured throughput, the bugs the load test found, and the honest limits are in [docs/scalability.md](docs/scalability.md). The business-impact panel on the home page separates measured figures from assumptions you can change. A script for the demo video is in [docs/video-script.md](docs/video-script.md).

## Account Aggregator adapter
`griha/aa.py` reads bank data in the ReBIT DEPOSIT FI format (XML or JSON, same names) from the public specification at specifications.rebit.org.in. It checks the mandatory fields and enumerations, then runs the same balance, holder and injection checks as a PDF statement. Upload one on the Apply page, or fetch a synthetic sample at `/api/samples/aa/<scenario>?format=xml`. Not built: the AA consent artefact, FIU request signing and payload decryption, which need a registered FIU.

Four RBI and MeitY primary texts have now been read in full: the HFC Directions 2025, the NBFC KYC Directions 2025, the NBFC Responsible Business Conduct Directions 2025 and the DPDP Rules 2025 (with the gazette notifications). The KFS follows the standardised Annex I format at `/case/<id>/kfs`, and our APR calculation reproduces the RBI's own worked example (17.07%). See `docs/security.md` for the duty-by-duty table.
