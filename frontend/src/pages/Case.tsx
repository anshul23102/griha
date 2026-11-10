import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowUp, ArrowDown, LinkSimple, Printer, Signpost as RouteIcon, ShieldCheck, Minus } from '@phosphor-icons/react'
import { api, applicantLink, session, inr, lakh, pct, type J } from '../api'
import { headlineOf, useI18n } from '../i18n'
import { STAGES, ST } from '../stages'
import { useCase } from '../useCase'
import { Board, Btn, Flap, Notice, RouteStrip, Sheet, Spinner, statusCls, type Outcome, type StationState } from '../components/kit'


export default function Case() {
  const { id } = useParams()
  const { t } = useI18n()
  const { c, prog, err, reload } = useCase(id)

  if (err) return <Notice tone="bad">{err}</Notice>
  if (!c && !prog) return <Spinner label={t('common.loading')} />
  if (!c) return <Running id={id!} prog={prog!} />
  if (c.erased) return <Erased c={c} />

  const d = c.decision
  const ev: J[] = d.evidence
  const byStage = Object.fromEntries(ev.map((e: J) => [e.stage, e]))
  const stations = STAGES.filter(s => byStage[s]).map(s => ({ key: s, label: t('stage.' + s), ms: byStage[s].ms, state: ST[byStage[s].status] as StationState }))
  const total = ev.reduce((a: number, e: J) => a + e.ms, 0)

  return (
    <div className="flex flex-col gap-6">
      <Board hi="आवेदन स्थिति" en="Application status" aside={<>{c.case_id}<br />{t('case.engine', { ms: total.toFixed(0) })}</>}>
        <p className="m-0 mt-2 font-medium">{c.applicant.name}, {c.applicant.age} · {t(c.loan.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP')} {lakh(c.loan.amount)} · {t('ap.years', { n: c.loan.tenure_months / 12 })}</p>
        <div className="mt-4"><RouteStrip stations={stations} label={t('case.route')} /></div>
      </Board>
      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr] items-start">
        <Ticket c={c} />
        {d.outcome === 'APPROVE' ? <Terms d={d} cooling={c.cooling_off_days} /> : <PathToYes c={c} />}
      </div>
      {d.outcome === 'REFER' && c.status === 'in_review' && <ReviewClock c={c} />}
      {d.outcome === 'REFER' && c.status !== 'in_review' && c.reviews.length > 0 && <ReviewDone r={c.reviews[c.reviews.length - 1]} />}
      <Reasons d={d} />
      {byStage.compliance && <Controls ctl={byStage.compliance.data.controls} />}
      <Evidence c={c} byStage={byStage} />
      {session() && d.outcome === 'REFER' && c.status === 'in_review' && <Review c={c} onDone={reload} />}
      {!session() && <DataRights c={c} onDone={reload} />}
    </div>
  )
}

function Running({ id, prog }: { id: string; prog: J }) {
  const { t } = useI18n()
  const done: J[] = prog.stages ?? []
  const stations = STAGES.map((s, i) => {
    const hit = done.find((e: J) => e.stage === s)
    return { key: s, label: t('stage.' + s), ms: hit?.ms, state: (hit ? ST[hit.status] : i === done.length ? 'run' : 'wait') as StationState }
  })
  const src: J[] = prog.sources ?? []
  return (
    <div className="flex flex-col gap-6">
      <Board hi="आवेदन स्थिति" en="Application status" aside={<>{id}<br />{t('case.running')}</>}>
        <p className="m-0 mt-2 font-medium">{t('case.running.b')}</p>
        <div className="mt-4"><RouteStrip stations={stations} label={t('case.route')} /></div>
      </Board>
      <Sheet title={t('run.sources')} sub={t('run.sources.sub')}>
        <ul className="list-none m-0 p-0 grid sm:grid-cols-4 divide-y-2 sm:divide-y-0 sm:divide-x-2 divide-faint">
          {['bank', 'bureau', 'kyc', 'land'].map(k => {
            const x = src.find((y: J) => y.source === k)
            const st = x?.status ?? 'pending'
            return (
              <li key={k} className="px-5 py-4">
                <div className="font-display font-bold">{t('run.src.' + k)}</div>
                <div className={`mt-1 inline-flex items-center gap-2 ${st === 'ok' ? 'text-ok' : st === 'failed' ? 'text-bad' : 'text-ink2'}`}>
                  {st === 'pending' ? <Spinner /> : null}{t('run.state.' + st)}
                  {x?.attempts > 1 && <span className="mono text-xs text-wait">{t('run.attempts', { n: x.attempts })}</span>}
                </div>
              </li>)
          })}
        </ul>
      </Sheet>
    </div>
  )
}

function DataRights({ c, onDone }: { c: J; onDone: () => void }) {
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  async function go(kind: string) {
    setBusy(true); setErr(null)
    try { const r = await api(`/cases/${c.case_id}/rights`, { kind }); setMsg(t('rights.done', { ref: r.reference, date: r.respond_by })); onDone() }
    catch (e) { setErr((e as Error).message) }
    setBusy(false)
  }
  const ret = c.retention?.hold && c.retention.until
  return (
    <Sheet title={t('rights.title')} sub={t('rights.sub')}>
      <div className="px-5 py-4 grid gap-3">
        {c.consent_withdrawn && <Notice tone="warn">{t('rights.withdrawn')}</Notice>}
        {ret && <Notice tone="info">{t('rights.retain', { date: c.retention.until })}</Notice>}
        <div className="flex flex-wrap gap-3">
          <Btn kind="ghost" disabled={busy || c.consent_withdrawn} onClick={() => go('withdraw_consent')}>{t('rights.withdraw')}</Btn>
          <Btn kind="ghost" disabled={busy} onClick={() => go('access')}>{t('rights.access')}</Btn>
          <Btn kind="ghost" disabled={busy} onClick={() => go('correction')}>{t('rights.correct')}</Btn>
          <Btn kind="danger" disabled={busy} onClick={() => go('erasure')}>{t('rights.erase')}</Btn>
        </div>
        {msg && <Notice tone="ok">{msg}</Notice>}
        {err && <Notice tone="bad">{err}</Notice>}
        {c.rights?.length > 0 && <ul className="m-0 pl-5 text-sm">{c.rights.map((r: J) => <li key={r.reference}>{t('rights.k.' + r.kind)} · <span className="mono">{r.reference}</span> · {t('rights.by', { date: r.respond_by })}</li>)}</ul>}
        <p className="m-0 text-sm"><Link to="/privacy" className="underline">{t('nav.privacy')}</Link></p>
      </div>
    </Sheet>
  )
}

function ReviewDone({ r }: { r: J }) {
  const { t } = useI18n()
  return (
    <Notice tone={r.action === 'approve' ? 'ok' : r.action === 'decline' ? 'bad' : 'warn'} title={t('rev.done', { a: t('act.' + r.action) })}>
      {r.reviewer && <><span className="font-bold">{r.reviewer}</span>: {r.reason} </>}<span className="mono text-xs text-ink2">audit {r.hash}</span>
    </Notice>
  )
}

function ReviewClock({ c }: { c: J }) {
  const { t } = useI18n()
  const sla = c.workflow?.sla
  const [now, setNow] = useState(Date.now() / 1000)
  useEffect(() => { const i = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(i) }, [])
  if (!sla) return <Notice>{t('sla.inline')}</Notice>
  const left = Math.max(0, Math.round(sla.due_at - now))
  const fmt = (s: number) => s >= 3600 ? `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m` : `${Math.floor(s / 60)}m ${s % 60}s`
  return (
    <Notice tone={sla.escalated ? 'bad' : 'warn'} title={sla.escalated ? t('sla.escalated') : t('sla.waiting')}>
      {sla.escalated ? t('sla.escalated.b') : t('sla.left', { t: fmt(left) })}
      {c.workflow?.ui && session() && <> <a href={c.workflow.ui.replace('/uw-', '/review-')} target="_blank" rel="noreferrer" className="underline text-blue font-display font-bold">{t('sla.history')}</a></>}
    </Notice>
  )
}

function Erased({ c }: { c: J }) {
  const { t } = useI18n()
  return (
    <div className="flex flex-col gap-6">
      <Board hi="डेटा मिटाया गया" en="Personal data erased" aside={c.case_id} />
      <Sheet title={t('case.erased.t')}><p className="m-0 p-5 max-w-[65ch]">{t('case.erased.b')}</p>
        <table className="chart"><tbody>{c.audit.map((e: J) => <tr key={e.seq}><td className="mono">#{e.seq}</td><td>{e.event}</td><td className="r mono">{e.hash}</td></tr>)}</tbody></table></Sheet>
    </div>
  )
}

function Ticket({ c }: { c: J }) {
  const [copied, setCopied] = useState(false)
  const { t, tc, lang } = useI18n()
  const d = c.decision
  const o = d.outcome as Outcome
  const word = t(o === 'APPROVE' ? 'status.approved' : o === 'REFER' ? 'status.referred' : 'status.declined')
  return (
    <section className="ticket" aria-labelledby="tk-h">
      <div className="px-6 pt-5 pb-5 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3 text-sm text-ink2"><span>{t('case.pnr')}</span><span className="mono text-ink">{c.case_id}</span></div>
        <h2 id="tk-h" className={`m-0 ${statusCls(o)}`}><Flap word={lang === 'en' ? word.toUpperCase() : word} /></h2>
        <p className="m-0 text-[1.125rem] font-medium max-w-[60ch]">{headlineOf(d, t, tc, lang)}</p>
        {d.refer_queue && <p className="m-0 font-display font-semibold">{t('case.queue')}: {t('queue.' + d.refer_queue)}</p>}
        {d.pd && <p className="m-0 text-ink2 text-[0.9375rem]">{t('case.pd', { p: pct(d.pd.pd), lo: pct(d.pd.pd_lo), hi: pct(d.pd.pd_hi) })}</p>}
      </div>
      <div className="perf" />
      <dl className="m-0 px-6 py-4 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-3 text-[0.9375rem]" aria-label={t('case.fare')}>
        <div><dt className="text-sm text-ink2">{t('ap.name')}</dt><dd className="m-0 font-medium">{c.applicant.name}</dd></div>
        <div><dt className="text-sm text-ink2">{t('ap.product')}</dt><dd className="m-0 font-medium">{t(c.loan.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP')}</dd></div>
        <div><dt className="text-sm text-ink2">{t('ap.amount')}</dt><dd className="m-0 num">{inr(c.loan.amount)}</dd></div>
        <div><dt className="text-sm text-ink2">{t('ap.tenure')}</dt><dd className="m-0 num">{t('ap.years', { n: c.loan.tenure_months / 12 })}</dd></div>
      </dl>
      <div className="perf" />
      <div className="px-6 py-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-ink2 mono leading-relaxed">policy v{d.policy_version} · {d.policy_hash}<br />model {d.model_version}{c.audit[0] ? <> · audit {c.audit[0].hash}</> : null}</div>
        {c.workflow?.ui && session() && <a href={c.workflow.ui} target="_blank" rel="noreferrer" className="no-print underline text-blue font-display font-bold">{t('case.history')}</a>}
        <button type="button" onClick={() => { const l = applicantLink(c.case_id); if (l) void navigator.clipboard?.writeText(l).then(() => setCopied(true)) }} className="no-print inline-flex items-center gap-2 min-h-11 px-4 border-2 border-rule rounded-none font-display font-semibold hover:bg-ground"><LinkSimple size={18} weight="bold" aria-hidden />{copied ? t('case.link.done') : t('case.link')}</button>
        {d.outcome === 'APPROVE' && <Link to={`/case/${c.case_id}/kfs`} className="no-print inline-flex items-center gap-2 min-h-11 px-4 border-2 border-rule rounded-none font-display font-semibold hover:bg-ground"><Printer size={18} weight="bold" aria-hidden />{t('case.kfs')}</Link>}
        {d.outcome === 'APPROVE' && <Link to={`/case/${c.case_id}/mitc`} className="no-print inline-flex items-center gap-2 min-h-11 px-4 border-2 border-rule rounded-none font-display font-semibold hover:bg-ground"><Printer size={18} weight="bold" aria-hidden />{t('case.mitc')}</Link>}
        <Link to={`/case/${c.case_id}/letter`} className="no-print inline-flex items-center gap-2 min-h-11 px-4 border-2 border-rule rounded-none font-display font-semibold hover:bg-ground"><Printer size={18} weight="bold" aria-hidden />{t('case.letter')}</Link>
      </div>
    </section>
  )
}

function Terms({ d, cooling }: { d: J; cooling?: number }) {
  const { t } = useI18n()
  const k = d.kfs
  const rows: [string, string][] = [
    [t('kfs.amount'), inr(k.loan_amount)], [t('kfs.tenure'), t('ap.years', { n: k.tenure_months / 12 })], [t('kfs.rate'), `${k.interest_rate_annual_pct}%`],
    [t('kfs.emi'), inr(k.emi)], [t('kfs.fee'), inr(k.processing_fee)], [t('kfs.interest'), inr(k.total_interest)], [t('kfs.total'), inr(k.total_payable)], [t('kfs.apr'), `${k.apr_pct}%`],
  ]
  return (
    <Sheet title={t('kfs.title')} sub={t('kfs.sub')}>
      {d.offer.reduced && <div className="px-5 pt-4"><Notice tone="warn">{t('kfs.reduced', { req: inr(d.offer.requested), got: inr(d.offer.amount) })}</Notice></div>}
      <table className="chart"><tbody>{rows.map(([a, b]) => <tr key={a}><th scope="row">{a}</th><td className="r num">{b}</td></tr>)}</tbody></table>
      {k.other_disclosures && <dl className="m-0 px-5 py-3 border-t border-faint grid gap-2">{k.other_disclosures.map((x: J) => (
        <div key={x.id}><dt className="text-sm font-semibold">{x.label}{x.lender_to_set ? <span className="ml-2 text-xs font-medium text-wait">{t('kfs.lender')}</span> : null}</dt><dd className="m-0 text-sm text-ink2">{x.value} <span className="mono text-xs">({x.basis})</span></dd></div>))}</dl>}
      <p className="m-0 px-5 py-3 text-sm text-ink2 border-t border-faint">{k.foreclosure_charges}. {cooling ? t('kfs.cooling.v', { n: cooling }) + ' ' : ''}{t('kfs.note')}</p>
    </Sheet>
  )
}

function PathToYes({ c }: { c: J }) {
  const { t } = useI18n()
  const nav = useNavigate()
  const [opts, setOpts] = useState<J[] | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/cases/' + c.case_id + '/path-to-yes', {}).then(setOpts).catch(() => setOpts([])) }, [c.case_id])
  async function apply(o: J) {
    setBusy(true)
    try { nav('/case/' + (await api('/cases/' + c.case_id + '/retry', o.change)).case_id) } catch { setBusy(false) }
  }
  return (
    <Sheet title={t('pty.title')} sub={t('pty.sub')}>
      {!opts ? <div className="p-5"><Spinner label={t('pty.search')} /></div> : (
        <ul className="list-none m-0 p-0 divide-y divide-faint">
          {opts.map((o, i) => (
            <li key={i} className="px-5 py-4 flex items-center justify-between gap-4">
              <div className="flex gap-3"><RouteIcon size={22} weight="bold" aria-hidden className="mt-0.5 shrink-0" />
                <div><p className="m-0 font-medium">{o.message}</p>{o.offer && <p className="m-0 text-sm text-ink2">{t('pty.then', { r: o.offer.rate_pct, e: inr(o.offer.emi) })}</p>}</div></div>
              {o.actionable && <Btn kind="ghost" disabled={busy} onClick={() => apply(o)}>{t('pty.try')}</Btn>}
            </li>))}
        </ul>)}
    </Sheet>
  )
}

function Reasons({ d }: { d: J }) {
  const { t, tc, lang } = useI18n()
  const order = { adverse: 0, info: 1, favourable: 2 } as Record<string, number>
  const rs = [...d.reasons].sort((a: J, b: J) => order[a.direction] - order[b.direction])
  const eff = (r: J): [ReactNode, string] => r.direction === 'favourable'
    ? [<ArrowDown size={16} weight="bold" aria-hidden key="i" />, t('eff.for')] : r.direction === 'info' ? [<Minus size={16} weight="bold" aria-hidden key="i" />, t('eff.info')] : [<ArrowUp size={16} weight="bold" aria-hidden key="i" />, t('eff.against')]
  return (
    <Sheet title={t('why.title')} sub={t('why.sub')}>
      {rs.length === 0 ? <p className="m-0 p-5">{t('why.none')}</p> : (
        <div className="overflow-x-auto"><table className="chart min-w-[640px]">
          <thead><tr><th>{t('why.source')}</th><th>{t('why.finding')}</th><th>{t('why.effect')}</th></tr></thead>
          <tbody>{rs.map((r: J, i: number) => {
            const hi = lang === 'hi' ? tc(r.code) : ''
            const [icon, word] = eff(r)
            return (
              <tr key={i}>
                <td className="whitespace-nowrap">{t('src.' + r.kind)}</td>
                <td>{hi ? <><span lang="hi" className="block font-medium">{hi}</span><span className="block text-sm text-ink2">{r.text}</span></> : <span className="block">{r.text}</span>}<span className="mono text-xs text-ink2">{r.code}</span></td>
                <td className={`whitespace-nowrap font-display font-semibold ${r.direction === 'favourable' ? 'text-ok' : r.direction === 'adverse' ? 'text-bad' : 'text-ink2'}`}><span className="inline-flex items-center gap-1">{icon}{word}</span></td>
              </tr>)
          })}</tbody>
        </table></div>)}
    </Sheet>
  )
}

function Controls({ ctl }: { ctl: J[] }) {
  const { t } = useI18n()
  const tone = (s: string) => s === 'met' ? 'text-ok' : s === 'enforced' ? 'text-wait' : 'text-ink2'
  const basis = (b: string) => b === 'verified' ? 'bg-okbg text-ok' : b === 'internal' ? 'bg-ground text-ink2' : 'bg-waitbg text-wait'
  return (
    <Sheet title={t('comp.title')} sub={t('comp.sub')}>
      <div className="overflow-x-auto"><table className="chart min-w-[820px]">
        <thead><tr><th>{t('comp.control')}</th><th>{t('comp.source')}</th><th>{t('comp.status')}</th><th>{t('comp.evidence')}</th></tr></thead>
        <tbody>{ctl.map((c: J) => (
          <tr key={c.id}>
            <th scope="row" className="max-w-[28ch] font-bold">{c.title}</th>
            <td className="max-w-[34ch]"><span className="block">{c.clause}</span><span className={`inline-block mt-1 px-1.5 py-0.5 text-xs font-bold ${basis(c.basis)}`}>{t('reg.' + c.basis)}</span></td>
            <td className={`whitespace-nowrap font-display font-bold ${tone(c.status)}`}>{t('comp.' + c.status)}</td>
            <td className="max-w-[40ch] text-ink2">{c.evidence}</td>
          </tr>))}</tbody>
      </table></div>
    </Sheet>
  )
}

function Fold({ title, summary, open, children }: { title: string; summary: string; open?: boolean; children: ReactNode }) {
  return (
    <details open={open} className="group border-b-2 border-faint last:border-0">
      <summary className="list-none cursor-pointer px-5 py-4 flex items-baseline justify-between gap-4 hover:bg-ground [&::-webkit-details-marker]:hidden">
        <span className="font-display font-semibold text-lg">{title}</span>
        <span className="text-sm text-ink2 text-right">{summary}<span className="ml-2 inline-block transition-transform group-open:rotate-90" aria-hidden>›</span></span>
      </summary>
      <div className="px-5 pb-5">{children}</div>
    </details>
  )
}
const KV = ({ k, v }: { k: string; v: ReactNode }) => <div className="flex justify-between gap-3 py-1.5 border-b border-faint last:border-0"><dt className="text-ink2">{k}</dt><dd className="m-0 num text-right">{v}</dd></div>

function Evidence({ c, byStage }: { c: J; byStage: Record<string, J> }) {
  const { t } = useI18n()
  const inc = byStage.income?.data, prop = byStage.property?.data, fr = byStage.fraud?.data, risk = byStage.risk?.data, pol = byStage.policy?.data
  const max = Math.max(...(inc?.monthly_eligible ?? [1]), 1)
  const st = (s: string) => byStage[s]?.status !== 'ok'
  return (
    <Sheet title={t('ev.title')} sub={t('ev.sub')}>
      {byStage.data_integration && <Fold title={t('ev.sources')} summary={byStage.data_integration.summary} open={st('data_integration')}>
        <div className="overflow-x-auto"><table className="chart min-w-[560px]">
          <thead><tr><th>{t('ev.src')}</th><th>{t('src.status')}</th><th className="r">{t('ev.src.latency')}</th><th className="r">{t('ev.src.records')}</th><th>{t('ev.src.feeds')}</th></tr></thead>
          <tbody>{byStage.data_integration.data.sources.map((x: J) => (
            <tr key={x.id}><th scope="row" className="font-normal"><span className="block font-bold">{x.name}</span><span className="block text-sm text-ink2">{x.channel}</span></th>
              <td className={`font-display font-bold ${x.status === 'ok' ? 'text-ok' : 'text-bad'}`}>{t(x.status === 'ok' ? 'src.ok' : 'src.failed')}</td>
              <td className="r num">{x.latency_ms === null ? '-' : x.latency_ms + ' ms'}</td><td className="r num">{x.records}</td><td>{x.feeds.map((f: string) => t('stage.' + (f === 'income' ? 'income' : f))).join(', ')}</td></tr>))}</tbody>
        </table></div>
        <h4 className="text-base font-bold mt-5 mb-2">{t('ev.docs')}</h4>
        <div className="overflow-x-auto"><table className="chart min-w-[560px]"><tbody>{byStage.data_integration.data.documents.map((x: J) => (
          <tr key={x.id}><th scope="row" className="font-bold whitespace-nowrap">{x.name}</th>
            <td className={`font-display font-bold whitespace-nowrap ${x.status === 'verified' ? 'text-ok' : x.status === 'warning' ? 'text-wait' : 'text-bad'}`}>{t('doc.' + x.status)}</td>
            <td>{x.detail}<span className="block text-sm text-ink2">{x.method}</span></td></tr>))}</tbody></table></div>
      </Fold>}
      {inc && <Fold title={t('ev.income')} summary={byStage.income.summary} open={st('income')}>
        <dl className="m-0 grid gap-x-10 sm:grid-cols-2">
          <KV k={t('ev.assessed')} v={inr(inc.est_monthly_income)} /><KV k={t('ev.declared')} v={inr(c.applicant.declared_income)} />
          <KV k={t('ev.vol')} v={pct(inc.income_cv, 0)} /><KV k={t('ev.obl')} v={inr(inc.statement_obligations)} />
        </dl>
        <p className="text-sm text-ink2 mt-3 mb-2">{inc.method}</p>
        <div className="flex items-end gap-1.5 h-24" role="img" aria-label={t('ev.chart.alt')}>
          {inc.monthly_eligible.map((v: number, i: number) => <div key={i} title={inr(v)} className="flex-1 bg-ink" style={{ height: `${(v / max) * 100}%` }} />)}
        </div>
      </Fold>}
      {fr && <Fold title={t('ev.fraud')} summary={byStage.fraud.summary} open={st('fraud')}>
        {fr.flags.length ? <table className="chart"><tbody>{fr.flags.map((f: J) => <tr key={f.code}><td className="mono whitespace-nowrap">{f.code}</td><td>{f.text}</td><td className="r num">{f.weight.toFixed(2)}</td></tr>)}</tbody></table> : <p className="m-0">{t('ev.fraud.none')}</p>}
        {fr.graph && <p className="text-sm text-ink2 mt-3 mb-0">{t('ev.graph', { n: fr.graph.ring_size })}</p>}
        {fr.aml && <p className="text-sm mt-2 mb-0"><b>{t('ev.aml')}.</b> {t('ev.aml.line', { s: t(fr.aml.sanctions_hit ? 'common.yes' : 'common.no'), p: t(fr.aml.pep ? 'common.yes' : 'common.no'), c: pct(fr.aml.cash_share, 0), r: t(fr.aml.str_recommended ? 'common.yes' : 'common.no') })}</p>}
      </Fold>}
      {risk && <Fold title={t('ev.risk')} summary={byStage.risk.summary}>
        <div className="flex flex-wrap items-end gap-x-8 gap-y-2 mb-5 border-b-2 border-faint pb-4">
          <div><div className="text-sm text-ink2">{t('ev.score')}</div><div className="num text-[2.5rem] leading-none font-medium">{risk.score}</div></div>
          <div className="font-display font-bold text-2xl">{t('ev.score.band', { b: risk.band })}</div>
          <p className="m-0 text-sm text-ink2 max-w-[44ch]">{t('ev.score.note')}</p>
        </div>
        <ul className="list-none m-0 p-0 grid gap-2.5">
          {risk.drivers.map((d: J) => (
            <li key={d.feature} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto] gap-3 items-center">
              <span>{d.label}</span>
              <span className="relative h-3 bg-ground" aria-hidden><span className={`absolute top-0 h-3 ${d.direction === 'adverse' ? 'bg-bad left-1/2' : 'bg-ok right-1/2'}`} style={{ width: `${Math.min(50, Math.abs(d.log_odds) * 40)}%` }} /></span>
              <span className="num text-right whitespace-nowrap">{d.value} <span className={d.direction === 'adverse' ? 'text-bad' : 'text-ok'}>{d.direction === 'adverse' ? t('ev.raises') : t('ev.lowers')}</span></span>
            </li>))}
        </ul>
        <p className="text-sm text-ink2 mt-3 mb-0">{t('ev.conformal')}: {risk.conformal_set.length === 1 ? t(risk.conformal_set[0] === 0 ? 'ev.c.repay' : 'ev.c.default') : t('ev.c.unsure')}</p>
      </Fold>}
      {prop && <Fold title={t('ev.prop')} summary={byStage.property.summary} open={st('property')}>
        <dl className="m-0 grid gap-x-10 sm:grid-cols-2">
          <KV k={t('ev.pdecl')} v={lakh(prop.declared_value)} /><KV k={t('ev.pmodel')} v={`${lakh(prop.p10)} – ${lakh(prop.p90)}`} />
          <KV k={t('ev.passess')} v={lakh(prop.assessed_value)} /><KV k={t('ev.pcircle')} v={lakh(prop.circle_value)} />
        </dl>
        {prop.flags.map((f: J) => <p key={f.code} className="m-0 mt-2 text-wait font-medium">{f.text}</p>)}
        {c.market_context && <p className="m-0 mt-3 text-sm text-ink2">{c.market_context.city_yoy_pct !== null ? t('ev.market.city', { city: c.market_context.city, v: c.market_context.city_yoy_pct.toFixed(1), c: c.market_context.composite_yoy_pct.toFixed(1), q: c.market_context.quarter }) : t('ev.market.comp', { city: c.market_context.city, c: c.market_context.composite_yoy_pct.toFixed(1), q: c.market_context.quarter })} <a href={c.market_context.url} target="_blank" rel="noreferrer" className="underline text-blue font-display font-bold">{c.market_context.source}</a>. {t('ev.market.note')}</p>}
        <table className="chart mt-3"><thead><tr><th>{t('ev.comp')}</th><th className="r">{t('ev.area')}</th><th className="r">{t('ev.age')}</th><th className="r">{t('ev.value')}</th></tr></thead>
          <tbody>{prop.comparables.map((p: J, i: number) => <tr key={i}><td>{i + 1}</td><td className="r num">{p.area_sqft}</td><td className="r num">{p.age_years}</td><td className="r num">{lakh(p.value)}</td></tr>)}</tbody></table>
      </Fold>}
      {pol && <Fold title={t('ev.policy')} summary={byStage.policy.summary} open={st('policy')}>
        <table className="chart"><tbody>{pol.rules.map((r: J) => (
          <tr key={r.id}><td className={`font-display font-semibold whitespace-nowrap ${r.outcome === 'pass' ? 'text-ok' : r.outcome === 'refer' ? 'text-wait' : 'text-bad'}`}>{t('rule.' + r.outcome)}</td>
            <td>{r.title}</td><td className="mono text-ink2">{r.id}</td><td className="r num">{r.actual === null ? '-' : typeof r.actual === 'number' ? +r.actual.toFixed(2) : String(r.actual)}</td></tr>))}</tbody></table>
      </Fold>}
      <Fold title={t('ev.stmt')} summary={c.statement_source}><Statement s={c.statement} issues={c.doc_issues} /></Fold>
      <Fold title={t('ev.audit')} summary={t('ev.audit.sum', { n: c.audit.length })}>
        <table className="chart"><tbody>{c.audit.map((e: J) => <tr key={e.seq}><td className="mono">#{e.seq}</td><td>{e.event}</td><td className="r mono">{e.hash}</td></tr>)}</tbody></table>
        {c.reviews.map((r: J, i: number) => <p key={i} className="mt-3 mb-0"><b>{r.reviewer}</b> · {t('act.' + r.action)}: {r.reason}</p>)}
      </Fold>
    </Sheet>
  )
}

function Statement({ s, issues }: { s: J; issues: J[] }) {
  const { t } = useI18n()
  return (
    <div>
      {issues.map((i: J) => <Notice key={i.code} tone="warn" title={i.code}>{i.text}</Notice>)}
      <p className="text-sm text-ink2 my-2">{s.balance_breaks ? t('ev.breaks', { n: s.balance_breaks }) : t('ev.nobreaks', { n: s.count })}</p>
      <div className="max-h-80 overflow-auto border-2 border-faint">
        <table className="chart"><thead><tr><th>{t('ev.date')}</th><th>{t('ev.narr')}</th><th className="r">{t('ev.amt')}</th><th className="r">{t('ev.bal')}</th></tr></thead>
          <tbody>{s.transactions.map((x: J, i: number) => (
            <tr key={i} className={x.broken ? 'bg-badbg' : ''}><td className="num whitespace-nowrap">{x.d}</td><td className="mono">{x.narration}{x.broken && <b className="ml-2 text-bad">{t('ev.break')}</b>}</td>
              <td className={`r num ${x.amount < 0 ? 'text-bad' : 'text-ok'}`}>{inr(x.amount)}</td><td className="r num">{inr(x.balance)}</td></tr>))}</tbody></table>
      </div>
    </div>
  )
}

function Review({ c, onDone }: { c: J; onDone: () => void }) {
  const { t } = useI18n()
  const [reason, setReason] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)
  async function act(action: string) {
    setErr(null); setBusy(true)
    try { await api('/cases/' + c.case_id + '/review', { action, reason }); onDone() } catch (e) { setErr((e as Error).message); ref.current?.focus() }
    setBusy(false)
  }
  const ok = reason.trim().length >= 15
  return (
    <Sheet title={t('rev.title')} sub={t('rev.sub')}>
      <div className="p-5 grid gap-4">
        <label htmlFor="reason" className="font-display font-semibold">{t('rev.reason')}</label>
        <textarea id="reason" ref={ref} rows={3} value={reason} onChange={e => setReason(e.target.value)} className="w-full p-3 rounded-none bg-sheet text-ink border-2 border-rule" aria-describedby="reason-h" />
        <p id="reason-h" className="m-0 text-sm text-ink2">{t('rev.hint')}</p>
        {err && <Notice tone="bad">{err}</Notice>}
        <div className="flex flex-wrap items-center gap-3">
          <Btn onClick={() => act('approve')} disabled={!ok || busy}><ShieldCheck size={18} weight="bold" aria-hidden />{t('act.approve')}</Btn>
          <Btn kind="ghost" onClick={() => act('request_documents')} disabled={!ok || busy}>{t('act.request_documents')}</Btn>
          <span className="flex-1 min-w-8" />
          <Btn kind="danger" onClick={() => act('decline')} disabled={!ok || busy}>{t('act.decline')}</Btn>
        </div>
      </div>
    </Sheet>
  )
}
