# Griha: Automated Mortgage Underwriting Engine (Hero Housing Fintech Challenge, PS2)

Status: working spec. Author is a solo builder; submission deadline 12th (assumed 12 Dec 2026; verify).

## 1. Intent
A pilot-grade, explainable, regulator-aware underwriting engine for Home Loans and LAP that a lender could put behind a real origination system. Target borrower: self-employed / informal-income, Tier 2/3 (inferred, not confirmed by Hero). Success = every one of the 8 PS2 points demonstrably covered, scored well on: accuracy/feasibility, use of data, explainability, regulatory fit, scalability, presentation clarity.

Honesty rules: all applicant data is synthetic and labelled; external integrations are mock adapters shaped like the real specs (Account Aggregator FI schema, bureau, KYC, GST, CERSAI); model metrics are reported on synthetic data only and say so.

## 2. Core principle
**The LLM never decides.** LLMs read and extract (documents, statements), draft (policy rules from PDF, borrower-language explanations). A deterministic, versioned, replayable engine decides. Every decision is reproducible from stored inputs + policy version + model version.

## 3. Pipeline (one stage = one module, one evidence record each)
1. Intake and consent: DPDP-style consent artefact, purpose-limited, timestamped.
2. Data adapters: AA bank data, bureau, KYC, GST, property/CERSAI. Common interface; fixtures + failure injection (timeouts, partial data).
3. Document intelligence: schema-constrained extraction (Claude vision when API key present; deterministic parser fallback). Output validated by Pydantic; arithmetic cross-checks.
4. Income engine (cash-flow underwriting): classify credits (salary/business/transfer/loan), detect obligations (EMIs), conservative income = percentile of trailing months with volatility haircut. Handles informal and seasonal income.
5. Fraud and KYC/AML: balance-continuity tamper check, round-trip/circular flow detection, velocity, entity graph (shared phone/address/employer/property), isolation-forest anomaly, name/DOB match, sanctions/PEP list screen (fixture).
6. Property: hedonic valuation + comparables, circle-rate sanity check, LTV, title/encumbrance flags.
7. Policy engine: policy-as-code (YAML), versioned and hashed, evaluates with full trace (rule, input, threshold, pass/fail). Hard rules reject, soft rules refer.
8. Risk scoring: monotonic-constrained LightGBM PD model, isotonic calibration, SHAP reason codes, conformal interval for confidence. Risk-based pricing and offer sizing.
9. Decision: APPROVE / REJECT / REFER with reasons, offer, Key Fact Statement (APR computed), adverse-action reasons.
10. Governance: hash-chained append-only audit log, decision replay, model card, fairness report, human override with mandatory reason.

## 4. Differentiators (the "cherry on top")
- **Path to Yes**: counterfactual search for rejected/referred cases ("approved if loan reduced to X or co-applicant income added"), actionable and honest.
- **Policy Impact Simulator**: credit head edits a rule threshold, replays the stored portfolio, sees approval-rate and expected-loss change before shipping the policy.
- **Replayable decisions**: re-run any decision byte-for-byte from the audit record.
- Stretch: borrower explanation in Hindi; underwriter copilot for REFER cases.

## 5. Security and compliance
Role-based access (borrower, underwriter, admin) with signed tokens; PII field encryption at rest (Fernet), Aadhaar never stored (token + last 4), PAN masked in logs; upload validation (type, size, magic bytes); rate limiting; strict CORS/headers; prompt-injection defence (documents are data, schema-constrained outputs, no tool access for extraction model); consent and erasure endpoints; no secrets in repo. Compliance mapping page: RBI HFC Directions 2025, Digital Lending Directions 2025 (KFS, APR), FREE-AI recommendations (non-binding), KYC/AML, Fair Practices, DPDP. Note the problem statement says NHB; HFC regulation now sits with the RBI. Exact clauses to be verified against primary RBI text before citing.

## 6. Architecture
Backend: Python 3.11, FastAPI, SQLModel (SQLite now, Postgres-ready), stages as pure functions over a typed `Case`, orchestrated as a DAG with per-stage timing. Frontend: React + TypeScript + Vite + Tailwind; screens: borrower flow with live pipeline progress, decision page, underwriter console, governance, policy simulator. Scalability story: stateless workers, queue per stage, idempotent stage keys, adapter circuit breakers (documented; single process implemented).

## 7. Phases
- P0 Foundation: spec, repo, tooling.
- P1 Core engine slice (backend): synthetic world, adapters, income, policy, risk, decision, audit, tests. **First submittable slice.**
- P2 API and frontend core flow.
- P3 Fraud depth, document intelligence, property module.
- P4 Governance, Path to Yes, Policy Simulator.
- P5 Security hardening, polish, submission pack (architecture diagram, deck, demo script).

## 8. Open items
Deadline date unconfirmed. Submission format unconfirmed. Anthropic API key not set (LLM paths fall back to deterministic).
