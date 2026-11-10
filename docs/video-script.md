# Demo video script (about 3 minutes)

Rules for this video: use only things the product shows itself. Say "synthetic" whenever applicants appear. Do not quote any figure from the Freddie Mac check unless Freddie Mac has confirmed in writing that you may. Record at 1080p, dark theme, English (a Hindi toggle moment is in the script).

## Before recording
- Full stack running on the laptop: `ops/start.sh`. Open Temporal (localhost:8233) and Grafana (localhost:3000) in two tabs.
- Run 8 to 10 cases from the home page first (include the referred ones) so the desk, Operations and the drift panel are not empty.
- Sign in once as officer@griha.demo and admin@griha.demo in separate windows.
- Close other apps, silence notifications, hide bookmarks.

## Script

| Time | On screen | Say |
|---|---|---|
| 0:00 | Home page | "A home-loan file normally waits days for an officer. Griha decides the clear cases in milliseconds, explains every decision, and sends the rest to a person with the evidence ready. Every applicant you will see is synthetic." |
| 0:15 | Run a live case (approve) | "One click runs the real engine: data, income, property, fraud, eligibility, policy, risk, compliance. About thirty milliseconds of compute." |
| 0:30 | Open the full case | "The decision comes with reasons, a Key Fact Statement with the all-in cost, and a cooling-off exit. These follow the RBI's housing finance directions, read in the primary text." Click the terms sheet briefly. |
| 0:50 | Evidence, regulatory controls | "Fifteen controls per case, each with its clause and how well we verified it." |
| 1:05 | Apply, flaky bureau, submit | "I apply with a bureau that fails twice. The workflow retries and the case still completes. Here is the real history in Temporal: attempt three." Switch to the Temporal tab, show the timeline, then the encrypted input: "Personal data inside the workflow engine is ciphertext." |
| 1:30 | Referred case, desk | "Risky cases go to a queue. Fraud-flagged approvals need the Credit Head. A timer escalates a stale case and writes it to the audit." Sign in, review a case. |
| 1:50 | Governance: verify chain, replay | "Every decision is in a hash-chained log. I can replay it byte for byte. If the engine has changed since, replay says so instead of crying tampering." |
| 2:05 | Erase a case | "Erasing a case destroys its key. The record stays, the data is gone." |
| 2:15 | Simulator | "Before changing a policy threshold I replay a portfolio and check fairness." |
| 2:30 | Operations, Grafana | "Live metrics, retries, model drift." |
| 2:40 | Data sources page | "Where each number comes from: RBI repo rate, NHB price index, and what is synthetic. We list what we rejected, too." |
| 2:50 | Business impact panel | "Measured: how many cases the engine decides alone. Assumed: officer minutes and cost, which you can change." |
| 3:00 | Close on hosted link | "Free to run, open to inspect. The link is in the submission." |

## Questions to be ready for
- Why is a simple logistic model as good as your boosted one? It is on the model card: they are indistinguishable on synthetic data, so we ship the monotone, explainable one.
- Is the data real? No. The page says which parts are published figures and which are synthetic.
- What happens when the bureau is down? Retries, then a referral to the data queue. Shown in the video.
- How does it scale? `docs/scalability.md`: measured, with its limits.
