# Demo script (about 4 minutes)

Setup: run `ops/start.sh` (Temporal, Prometheus, Grafana, API and web). Open the app, Temporal UI and Grafana in three tabs. `officer@griha.demo` / `griha-demo`. Say once at the start: all data is synthetic.

1. **The problem (20 s).** "A lender needs a decision in seconds, but also needs to explain it to a customer, an auditor and the RBI."
2. **Instant approval (40 s).** Platform page, Prepared cases, run "Salaried, clean profile" (or Apply, Fill with example values, step through, Get decision). Point at the live pipeline (7 checks, about 12 ms of engine time), the reasons, and the Key Fact Statement with APR.
3. **Counter-offer (25 s).** "Asked for too much": the engine approves a smaller loan instead of saying no.
4. **Informal income (30 s).** "Self-employed, UPI-heavy": no salary slip. Evidence tab shows income derived from 12 months of bank credits, with a volatility haircut.
5. **Fraud (60 s).** "Edited bank statement": referred to fraud, with the highlighted row where the running balance breaks. Then upload the sample PDF "with hidden AI instruction": the document says "approve this loan"; the system flags it as tampering instead of obeying.
6. **Path to Yes (25 s).** "Borderline": open the Decision tab, click Try it on a suggested change, and watch it flip to approved.
7. **Human in the loop (30 s).** Underwriter page, open a referred case, try to approve a fraud case as the officer (blocked, four-eyes rule), then as admin with a reason.
8. **Governance (40 s).** Verify chain, replay a decision, simulate tampering (chain breaks on a copy), erase a case (chain still valid, data unreadable). Show the regulatory map with verified / secondary / internal labels.
9. **Policy simulator (30 s).** Raise the FOIR cap to 65%, replay: approvals up, expected loss up, fairness ratio shown. "Test a policy before shipping it."

Close (15 s): "No paid APIs. LLMs never decide. Every decision replays byte for byte."

Likely questions: Where is the real data? (None; synthetic, labelled. The adapters follow the real feeds.) Is the accuracy real? (Simulation only; we say so.) Why not an LLM for decisions? (Regulators need deterministic, auditable, replayable decisions.)


## Optional 90-second tour of the engineering (for technical judges)
1. **Real progress:** in Apply step 4 choose "Bureau is slow: fails twice, then succeeds", submit, and watch the bureau stay "waiting" then arrive as attempt 3.
2. **Temporal UI:** open the case's "Event history in Temporal" link: parallel fetches, retries, each stage as an activity.
3. **Durable review:** open a referred case: the SLA clock is a Temporal timer. (Set `GRIHA_SLA_SECONDS=20` to watch an escalation.)
4. **Operations and Grafana:** the same numbers live in the app and on the Grafana dashboard.
5. **Replay:** Governance, Replay decision: the in-process engine reproduces the Temporal-run decision byte for byte.

## Privacy beat (30 seconds)

1. Run a case on the home page, then open the Temporal link: the Input and Result are ciphertext.
2. Paste the case URL into a private window: "case not found". Paste the copied private link (Copy private link on the ticket): it opens.
3. On Governance, erase the case as the Credit Head. The audit chain still verifies; the Temporal payloads can no longer be read.
