import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, pct, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Sheet } from '../components/kit'

type Row = { n: number; req: string; built: string; see: [string, string][]; proof: string; limit: string }

export default function Coverage() {
  const { t } = useI18n()
  const [mc, setMc] = useState<J | null>(null)
  const [stats, setStats] = useState<J | null>(null)
  useEffect(() => { api('/model-card').then(setMc).catch(() => {}); api('/stats').then(setStats).catch(() => {}) }, [])
  const m = mc?.metrics
  const ms = stats?.engine_ms_median
  const rows: Row[] = [
    { n: 1, req: 'Integrate data sources. Connect to multiple external sources and show how data flows into the engine.',
      built: 'Four source adapters (bank statement or Account Aggregator, credit bureau, KYC and sanctions, land records). Every case lists each source with its channel, time, record count and the stages it feeds. A source that is down sends the case to the Data queue: nothing is guessed.',
      see: [['Case › Evidence › Data sources and documents', '/'], ['Apply, step 4: outage test', '/apply']], proof: '4 sources per case, each timed and traced to the stages that use it.',
      limit: 'Bureau, KYC and land records are simulated and shaped like the real feeds; there is no live Account Aggregator, bureau or KYC access. The sanctions screen is real: it runs against the UN Security Council Consolidated List (10 Nov 2026 snapshot).' },
    { n: 2, req: 'Eligibility and policy. Assess eligibility in real time for Home Loans and LAP and validate each case against credit policy.',
      built: 'An instant "what can I borrow" check and, per case, eligibility sizing: FOIR at a stress rate, tiered LTV caps, tenure caps and ticket limits for both products. Eighteen policy rules written as code, hashed, traced line by line. A smaller counter-offer replaces a flat no.',
      see: [['Home › What can I borrow?', '/'], ['Case › Policy trace', '/']], proof: ms ? `Median engine time ${ms} ms per case.` : 'Median engine time shown on the home page.',
      limit: 'FOIR, age and cut-offs are illustrative. Hero Housing’s real credit policy was not available.' },
    { n: 3, req: 'Fraud detection and KYC/AML. Detect fraud and meet KYC/AML requirements without manual review.',
      built: 'Balance-arithmetic tamper check, circular money flows, window dressing, cash intensity, linked-applicant graph, behaviour anomaly model, name match, screening against the UN Security Council list, and a suspicious-transaction signal. Flags raise the case automatically.',
      see: [['Case › Evidence › Fraud and KYC/AML', '/'], ['Prepared cases P07 to P10', '/']], proof: 'On injected typologies, edited statements, window dressing, identity mismatch and rings were held back in 119 of 120 cases. Inflated declared income is flagged but not blocked, because we price on income verified from the statement.',
      limit: 'The typologies are ones we wrote. Real fraud differs. No device or behavioural-biometric signals.' },
    { n: 4, req: 'Risk scoring. Score the risk of every application and show how the score is produced.',
      built: 'A monotone-constrained boosted model with calibrated probabilities, a conformal confidence set, native SHAP drivers and a scorecard number (650 points at 30:1 odds, 40 points per doubling) with a band from A to E that sets the price.',
      see: [['Case › Evidence › Risk model drivers', '/'], ['Governance › Model card', '/governance']], proof: m ? `AUC ${m.risk.auc.toFixed(2)}, KS ${m.risk.ks.toFixed(2)}, predicted ${pct(m.risk.mean_pred_test)} vs actual ${pct(m.risk.actual_test)}. Calibration by decile and baselines are on the Governance page.` : 'Metrics on the Governance page.',
      limit: 'Synthetic data. A plain logistic regression scores about the same here (the simulated truth is near-linear). We say so on the model card.' },
    { n: 5, req: 'Documents and property. Verify documents digitally and assess the property within the same flow.',
      built: 'Uploaded statements are read by a text parser or an optional local model, cross-checked, and scanned for hidden instructions. A document table lists PAN, Aadhaar e-KYC, bank statement, income proof and property title with a status each. The property gets a value range from comparable sales, a circle-rate check and title flags in the same run.',
      see: [['Apply, step 4: upload a PDF', '/apply'], ['Case › Evidence › Property', '/']], proof: m ? `Property value within 10% of truth on ${pct(m.property.ppe10, 0)} of test cases.` : 'Valuation accuracy on the Governance page.',
      limit: 'Scanned or unfamiliar layouts need the local model, which is slow on small hardware. Land records are simulated.' },
    { n: 6, req: 'Compliance checks. Show how NHB regulations, Fair Practices Code and audit standards are built into the engine.',
      built: 'Fifteen regulatory controls are evaluated and evidenced on every case: KYC, AML, STR signal, LTV cap, consent, Key Fact Statement and APR, pre-payment disclosure, grievance route, written reasons, fairness, human oversight, four-eyes, audit and encryption. Each shows its clause, how well we verified that source, and what the engine did here. Housing-finance regulation moved from the NHB to the RBI in 2019; we cite the RBI.',
      see: [['Case › Regulatory controls on this case', '/'], ['Governance › Regulatory mapping', '/governance']], proof: '15 controls per case (the applicant sees 11; AML, STR, EDD and four-eyes are withheld). Verified in RBI text: the HFC LTV caps (para 58), the Fair Practices Code, the KYC Directions and the DPDP Rules.',
      limit: 'The Fair Practices Code chapter was not read. Prepayment, KFS and FREE-AI points come from secondary sources, and several thresholds are internal. Each is labelled.' },
    { n: 7, req: 'Instant decisioning. Deliver a humanless decision instantly: approve, reject or refer.',
      built: 'An outcome in a few milliseconds with reasons, a priced offer, a Key Fact Statement with APR, four refer queues (data, fraud, credit, property), and a Path to Yes that finds the smallest change that flips a decline.',
      see: [['Home › Run a live case', '/'], ['Governance › Capacity', '/governance']], proof: ms ? `Median ${ms} ms. Capacity is measured on the Governance page.` : 'Capacity on the Governance page.',
      limit: 'In production, bureau and bank calls dominate latency, not the decision.' },
    { n: 8, req: 'Explainability and governance. Every decision must be explainable, traceable and audit-ready.',
      built: 'Reasons on every outcome, an evidence trail behind each, byte-for-byte replay from encrypted inputs, a hash-chained audit log, tamper detection, per-case encryption with erasure, four-eyes on fraud overrides, a policy simulator with a fairness check, and a model card.',
      see: [['Governance › Audit controls', '/governance'], ['Policy simulator', '/simulator']], proof: 'Replay and tamper detection are covered by automated tests.',
      limit: 'The engine’s detailed sentences are English; Hindi shows translated titles. The Key Facts Statement and the privacy notice are fully Hindi (the Hindi KFS awaits a legal translator’s review). Fairness is reported per attribute with a 95% interval; the groups are synthetic.' },
  ]
  const crit: [string, string, string, string][] = [
    ['Accuracy and feasibility', 'Calibration by decile, a comparison with simple baselines, and an honest note that the data is synthetic. Feasibility: shadow-mode pilot on a lender’s own history, then live.', '/governance', 'Governance'],
    ['Use of data', 'Bank cash flow, statement forensics, bureau, KYC and sanctions, land and title records, comparable sales, and a linked-applicant graph, all merged per case with lineage.', '/', 'Case evidence'],
    ['Explainability', 'Reasons, evidence folds, scorecard, SHAP drivers, Path to Yes, and a printable decision letter in English or Hindi.', '/', 'Case'],
    ['Regulatory fit', 'Fifteen controls per case with clause and verification status, RBI as the regulator, DPDP-aligned consent and erasure.', '/governance', 'Governance'],
    ['Scalability', 'Stateless stages, idempotent decisions, one worker measured on this machine, and the worker count for a million cases a day. Queue and database are designed, not built.', '/governance', 'Capacity'],
    ['Clarity of presentation', 'This page, a four-minute demo script, an architecture diagram, a deck and a live demo on the home page.', '/', 'Home'],
  ]
  const api_rows: [string, string, string][] = [
    ['POST', '/api/applications/new', 'Submit an application. Returns the decision with every stage’s evidence.'],
    ['POST', '/api/documents/statement', 'Upload a bank-statement PDF. Returns what was read and any document issues.'],
    ['POST', '/api/eligibility', 'Instant pre-qualification with the same policy numbers.'],
    ['GET', '/api/cases/{id}', 'Read a case: decision, evidence, reviews, audit entries.'],
    ['POST', '/api/cases/{id}/path-to-yes', 'The smallest changes that would turn a decline into an approval.'],
    ['POST', '/api/cases/{id}/retry', 'Re-run a case with changed amount, tenure or co-applicant.'],
    ['POST', '/api/cases/{id}/review', 'Officer decision on a referred case. Reason required; four-eyes on fraud.'],
    ['POST', '/api/audit/replay/{id}', 'Re-execute a recorded decision and compare the digest.'],
    ['GET', '/api/audit/verify', 'Verify the hash chain.'],
    ['POST', '/api/simulate', 'Replay a stored portfolio under a changed policy.'],
    ['POST', '/api/cases/{id}/erase', 'Erase personal data by destroying the case key.'],
    ['GET', '/api/benchmark', 'Measure engine capacity on this machine.'],
  ]
  return (
    <div className="flex flex-col gap-10">
      <Board hi="PS2 जाँच-सूची" en="PS2 checklist"><p className="m-0 mt-3 max-w-[64ch] text-[1.125rem] font-medium">{t('cov.lead')}</p></Board>

      <Sheet title={t('cov.req')} sub="Problem Statement 2: Digitally Automated Mortgage Underwriting Engine, Hero Housing Fintech Challenge.">
        <ol className="list-none m-0 p-0">
          {rows.map(r => (
            <li key={r.n} className="grid gap-x-6 gap-y-4 px-5 py-6 border-b-2 border-faint last:border-0 md:grid-cols-[3.5rem_1fr]">
              <span className="plat-no" aria-hidden>{r.n}</span>
              <div className="grid gap-4 min-w-0">
                <h3 className="text-xl font-bold max-w-[70ch]">{r.req}</h3>
                <p className="m-0 max-w-[80ch]">{r.built}</p>
                <div className="grid gap-4 md:grid-cols-3">
                  <div><h4 className="text-sm font-bold text-ink2 mb-1">{t('cov.col.see')}</h4><ul className="list-none m-0 p-0 grid gap-1">{r.see.map(([l, to]) => <li key={l}><Link to={to} className="underline text-blue">{l}</Link></li>)}</ul></div>
                  <div><h4 className="text-sm font-bold text-ink2 mb-1">{t('cov.col.proof')}</h4><p className="m-0">{r.proof}</p></div>
                  <div><h4 className="text-sm font-bold text-wait mb-1">{t('cov.col.limit')}</h4><p className="m-0 text-ink2">{r.limit}</p></div>
                </div>
              </div>
            </li>))}
        </ol>
      </Sheet>

      <Sheet title={t('cov.crit')} sub="The six things the judges score.">
        <div className="overflow-x-auto"><table className="chart min-w-[560px]"><thead><tr><th>{t('cov.col.crit')}</th><th>{t('cov.col.how')}</th><th>{t('cov.col.see')}</th></tr></thead>
          <tbody>{crit.map(([c, h, to, l]) => <tr key={c}><th scope="row" className="font-bold whitespace-nowrap">{c}</th><td className="max-w-[70ch]">{h}</td><td><Link to={to} className="underline text-blue">{l}</Link></td></tr>)}</tbody></table></div>
      </Sheet>

      <Sheet title={t('cov.api')} sub="A lender integrates over REST. Each call below is live in this prototype.">
        <div className="overflow-x-auto"><table className="chart min-w-[640px]"><tbody>{api_rows.map(([mth, p, d]) => (
          <tr key={p}><td className="mono font-bold">{mth}</td><td className="mono">{p}</td><td>{d}</td></tr>))}</tbody></table></div>
      </Sheet>
    </div>
  )
}
