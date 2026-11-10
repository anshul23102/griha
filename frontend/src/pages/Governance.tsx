import { useEffect, useState } from 'react'
import { ArrowDown, ArrowUp, Minus, ShieldCheck, ShieldWarning } from '@phosphor-icons/react'
import { api, session, pct, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Notice, Sheet, Spinner } from '../components/kit'

export default function Governance() {
  const { t } = useI18n()
  const [user, setUser] = useState(session())
  const [mc, setMc] = useState<J | null>(null)
  const [pol, setPol] = useState<J | null>(null)
  const [cases, setCases] = useState<J[]>([])
  const [sel, setSel] = useState('')
  const [verify, setVerify] = useState<J | null>(null)
  const [replay, setReplay] = useState<J | null>(null)
  const [tamper, setTamper] = useState<J | null>(null)
  const [erased, setErased] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [bench, setBench] = useState<J | null>(null)
  const [benching, setBenching] = useState(false)
  const [breaches, setBreaches] = useState<J[]>([])
  const [bf, setBf] = useState({ description: '', nature: 'confidentiality', affected_count: 0 })
  const loadBreaches = () => api('/breaches').then(setBreaches).catch(() => setBreaches([]))
  useEffect(() => { if (user?.role === 'admin') loadBreaches() }, [user])
  useEffect(() => { const h = () => setUser(session()); window.addEventListener('griha-auth', h); return () => window.removeEventListener('griha-auth', h) }, [])
  useEffect(() => { api('/model-card').then(setMc).catch(e => setErr(e.message)); api('/policy').then(setPol).catch(e => setErr(e.message)) }, [])
  useEffect(() => {
    if (!user) return
    api('/cases').then((r: J[]) => { setCases(r); setSel(s => s || r[0]?.case_id || '') }).catch(() => {})
  }, [user, erased])
  const run = async (f: () => Promise<void>) => { setErr(null); try { await f() } catch (e) { setErr((e as Error).message) } }
  const m = mc?.metrics
  const admin = user?.role === 'admin'
  const sig = (s: string) => s === 'verified' ? 'bg-okbg text-ok' : s === 'internal' ? 'bg-ground text-ink2' : 'bg-waitbg text-wait'

  return (
    <div className="flex flex-col gap-6">
      <Board hi="शासन एवं अनुपालन" en="Governance and compliance" aside={pol ? <>policy v{pol.version}<br />{pol.hash}</> : undefined}>
        <p className="m-0 mt-2 font-medium max-w-[62ch]">{t('gov.lead')}</p>
      </Board>
      {err && <Notice tone="bad">{err}</Notice>}

      <Sheet title={t('gov.audit')} sub={t('gov.audit.sub')}>
        {!user ? <p className="m-0 p-5">{t('gov.signin')}</p> : (
          <div className="p-5 grid gap-6">
            <div className="flex flex-wrap items-center gap-4">
              <Btn onClick={() => run(async () => setVerify(await api('/audit/verify')))}><ShieldCheck size={18} weight="bold" aria-hidden />{t('gov.verify')}</Btn>
              {verify && (verify.ok
                ? <span className="inline-flex items-center gap-2 text-ok font-display font-semibold"><ShieldCheck size={22} weight="fill" aria-hidden />{t('gov.intact', { n: verify.entries })} <span className="mono text-ink2 font-normal">{verify.head?.slice(0, 16)}</span></span>
                : <span className="inline-flex items-center gap-2 text-bad font-display font-semibold"><ShieldWarning size={22} weight="fill" aria-hidden />{t('gov.broken', { n: verify.broken_at })}</span>)}
            </div>
            <div className="grid gap-3">
              <label htmlFor="gcase" className="font-display font-semibold">{t('gov.case')}</label>
              <select id="gcase" value={sel} onChange={e => setSel(e.target.value)} className="min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none max-w-xl">
                {cases.length === 0 && <option value="">{t('gov.nocases')}</option>}
                {cases.map(c => <option key={c.case_id} value={c.case_id}>{c.case_id} · {c.name} · {t(c.outcome === 'APPROVE' ? 'status.approved' : c.outcome === 'REFER' ? 'status.referred' : 'status.declined')}</option>)}
              </select>
              <div className="flex flex-wrap gap-3">
                <Btn kind="ghost" disabled={!sel} onClick={() => run(async () => setReplay(await api('/audit/replay/' + sel, {})))}>{t('gov.replay')}</Btn>
                <Btn kind="ghost" disabled={!sel || !admin} onClick={() => run(async () => setTamper(await api('/audit/tamper-demo/' + sel, {})))}>{t('gov.tamper')}</Btn>
              </div>
              {!admin && <p className="m-0 text-sm text-ink2">{t('gov.admin.only')}</p>}
              {replay && <Notice tone={replay.erased ? 'info' : replay.match ? 'ok' : replay.engine_match === false ? 'warn' : 'bad'}>{replay.erased ? t('gov.replay.erased', { o: replay.recorded_outcome }) : replay.match ? t('gov.replay.ok', { o: replay.replayed_outcome }) : replay.engine_match === false ? t('gov.replay.version', { a: replay.engine_recorded, b: replay.engine_current }) : t('gov.replay.bad')}</Notice>}
              {tamper && <Notice tone="warn">{t('gov.tamper.res', { n: tamper.forged_entry, b: tamper.verification.broken_at })}</Notice>}
            </div>
            <div className="border-t-2 border-faint pt-5 grid gap-3 max-w-xl">
              <h3 className="text-lg font-semibold">{t('gov.erase')}</h3>
              <p className="m-0 text-ink2">{t('gov.erase.b')}</p>
              <label htmlFor="ereason" className="font-display font-semibold">{t('gov.erase.reason')}</label>
              <input id="ereason" value={reason} onChange={e => setReason(e.target.value)} className="min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none" />
              <div><Btn kind="danger" disabled={!sel || !admin || reason.trim().length < 15} onClick={() => run(async () => { await api('/cases/' + sel + '/erase', { reason }); setErased(sel); setReason(''); setVerify(await api('/audit/verify')) })}>{t('gov.erase.go')}</Btn></div>
              {erased && <Notice tone="ok">{t('gov.erase.done', { id: erased })}</Notice>}
            </div>
          </div>)}
      </Sheet>

      {pol?.compliance && (
        <Sheet title={t('gov.reg')} sub={t('gov.reg.sub')}>
          <div className="overflow-x-auto"><table className="chart min-w-[720px]"><thead><tr><th>{t('gov.reg.topic')}</th><th>{t('gov.reg.source')}</th><th>{t('gov.reg.status')}</th></tr></thead>
            <tbody>{pol.compliance.map((c: J) => (
              <tr key={c.topic}><th scope="row" className="max-w-[30ch]"><span className="font-display font-semibold">{c.topic}</span><span className="block text-sm text-ink2 font-normal">{c.note}</span></th>
                <td className="max-w-[44ch]">{c.source}</td>
                <td><span className={`inline-block px-2 py-0.5 rounded-none font-display font-semibold text-sm ${sig(c.status)}`}>{t('reg.' + c.status)}</span></td></tr>))}</tbody></table></div>
        </Sheet>)}

      {!mc ? <Spinner label={t('common.loading')} /> : (
        <Sheet title={`${t('gov.model')} · ${mc.model_version}`} sub={t('gov.model.sub')}>
          <dl className="m-0 grid grid-cols-2 sm:grid-cols-5 divide-x-2 divide-faint border-b-2 border-faint">
            {[['AUC', m.risk.auc.toFixed(3)], ['KS', m.risk.ks.toFixed(3)], ['Brier', m.risk.brier.toFixed(4)], [t('gov.calib'), `${pct(m.risk.mean_pred_test)} / ${pct(m.risk.actual_test)}`], [t('gov.val'), pct(m.property.ppe10, 0)]].map(([k, v]) => (
              <div key={String(k)} className="px-4 py-3"><dt className="text-sm text-ink2">{k}</dt><dd className="m-0 num text-xl">{v}</dd></div>))}
          </dl>
          <div className="p-5 grid gap-5">
            <div><h3 className="text-lg font-semibold mb-2">{t('gov.mono')}</h3>
              <ul className="list-none m-0 p-0 grid gap-x-8 gap-y-1.5 sm:grid-cols-2 lg:grid-cols-3">{mc.features.map((f: J) => (
                <li key={f.name} className="flex items-center gap-2">{f.monotone > 0 ? <ArrowUp size={16} weight="bold" className="text-bad" aria-hidden /> : f.monotone < 0 ? <ArrowDown size={16} weight="bold" className="text-ok" aria-hidden /> : <Minus size={16} weight="bold" className="text-ink2" aria-hidden />}
                  <span>{f.name.replace(/_/g, ' ')}</span><span className="text-sm text-ink2">{f.monotone > 0 ? t('gov.mono.up') : f.monotone < 0 ? t('gov.mono.down') : t('gov.mono.free')}</span></li>))}</ul></div>
            <ul className="m-0 pl-5 text-ink2 grid gap-1">{mc.notes.map((n: string) => <li key={n}>{n}</li>)}</ul>
            <p className="m-0"><b>{t('gov.never')}</b> {mc.excluded.join(', ')}.</p>
          </div>
        </Sheet>)}

      {mc && m.risk.baselines && (
        <Sheet title={t('gov.base')} sub={t('gov.base.sub')}>
          <table className="chart"><tbody>{[['foir_only', 'gov.base.foir'], ['bureau_only', 'gov.base.bureau'], ['logistic', 'gov.base.logistic'], ['griha_gbm', 'gov.base.gbm']].map(([k, l]) => (
            <tr key={k}><th scope="row" className={k === 'griha_gbm' ? 'font-bold' : 'font-normal'}>{t(l)}</th>
              <td className="w-[40%]"><span className="block h-3 bg-ground" aria-hidden><span className={`block h-3 ${k === 'griha_gbm' ? 'bg-blue' : 'bg-ink2'}`} style={{ width: `${(m.risk.baselines[k] - 0.5) * 200}%` }} /></span></td>
              <td className="r num font-bold">{m.risk.baselines[k].toFixed(3)}</td></tr>))}</tbody></table>
          <p className="m-0 px-5 py-4 border-t border-faint text-ink2 max-w-[80ch]">{t('gov.base.note')}</p>
        </Sheet>)}

      {mc && mc.real_data && (
        <Sheet title={t('gov.real')} sub={t('gov.real.sub')}>
          <div className="overflow-x-auto"><table className="chart min-w-[560px]">
            <thead><tr><th>{t('gov.real.set')}</th><th className="r">n</th><th className="r">{t('gov.base.logistic')}</th><th className="r">{t('gov.real.free')}</th><th className="r">{t('gov.real.mono')}</th><th className="r">{t('gov.real.gap')}</th></tr></thead>
            <tbody>{mc.real_data.results.map((r: J) => (
              <tr key={r.dataset}><th scope="row" className="font-normal">{r.dataset}</th><td className="r num">{r.n.toLocaleString('en-IN')}</td>
                <td className="r num">{r.logit.auc.toFixed(3)}</td><td className="r num">{r.gbm_free.auc.toFixed(3)}</td><td className="r num font-bold">{r.gbm_monotone.auc.toFixed(3)}</td>
                <td className="r num">{pct(r.calibration_gap_mean_abs)}</td></tr>))}</tbody>
          </table></div>
          <p className="m-0 px-5 py-4 border-t border-faint text-ink2 max-w-[80ch]">{t('gov.real.note')}</p>
        </Sheet>)}

      {mc && m.risk.calibration && (
        <Sheet title={t('gov.calib.title')} sub={t('gov.calib.sub')}>
          <div className="overflow-x-auto"><table className="chart min-w-[520px]">
            <thead><tr><th>{t('gov.calib.bin')}</th><th className="r">{t('gov.calib.n')}</th><th className="r">{t('gov.calib.pred')}</th><th className="r">{t('gov.calib.act')}</th><th aria-hidden /></tr></thead>
            <tbody>{m.risk.calibration.map((b: J) => (
              <tr key={b.bin}><td className="num">{b.bin}</td><td className="r num">{b.n}</td><td className="r num">{pct(b.predicted)}</td><td className="r num">{pct(b.actual)}</td>
                <td className="w-[30%]" aria-hidden><span className="relative block h-3 bg-ground"><span className="absolute inset-y-0 left-0 bg-ink2" style={{ width: `${Math.min(100, b.predicted * 300)}%`, height: '50%' }} /><span className="absolute left-0 bottom-0 bg-blue" style={{ width: `${Math.min(100, b.actual * 300)}%`, height: '50%' }} /></span></td></tr>))}</tbody>
          </table></div>
        </Sheet>)}

      {admin && (
        <Sheet title={t('gov.breach')} sub={t('gov.breach.sub')}>
          <div className="px-5 py-4 grid gap-3 max-w-[760px]">
            <label className="grid gap-1 font-medium">{t('gov.breach.what')}
              <textarea className="w-full p-3 bg-sheet text-ink border-2 border-rule rounded-none" rows={2} value={bf.description} onChange={e => setBf({ ...bf, description: e.target.value })} /></label>
            <div className="flex flex-wrap gap-3 items-end">
              <label className="grid gap-1 font-medium">{t('gov.breach.nature')}
                <select className="min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none" value={bf.nature} onChange={e => setBf({ ...bf, nature: e.target.value })}>
                  {['confidentiality', 'integrity', 'availability'].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
              <label className="grid gap-1 font-medium">{t('gov.breach.count')}
                <input className="min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none w-32" type="number" min={0} value={bf.affected_count} onChange={e => setBf({ ...bf, affected_count: Number(e.target.value) })} /></label>
              <Btn disabled={bf.description.trim().length < 20} onClick={() => run(async () => { await api('/breaches', bf); setBf({ ...bf, description: '' }); await loadBreaches() })}>{t('gov.breach.log')}</Btn>
            </div>
          </div>
          {breaches.length > 0 && <div className="overflow-x-auto"><table className="chart min-w-[640px]">
            <thead><tr><th>{t('gov.breach.ref')}</th><th>{t('gov.breach.due')}</th><th>{t('gov.breach.open')}</th><th aria-hidden /></tr></thead>
            <tbody>{breaches.map((b: J) => (
              <tr key={b.reference}><td className="mono align-top">{b.reference}<div className="text-sm text-ink2 font-sans">{b.description}</div></td>
                <td className={`num align-top ${b.overdue ? 'text-bad font-bold' : ''}`}>{b.board_report_due.slice(0, 16).replace('T', ' ')}{b.overdue ? ' · ' + t('gov.breach.overdue') : ''}</td>
                <td className="align-top">{b.open.length ? b.open.join(', ') : t('gov.breach.done')}</td>
                <td className="align-top">{b.open.slice(0, 1).map((p: string) => (
                  <Btn key={p} onClick={() => run(async () => { await api(`/breaches/${b.reference}/notify`, { party: p, note: `${p} notified by ${user?.name ?? 'admin'}` }); await loadBreaches() })}>{t('gov.breach.mark', { p })}</Btn>))}</td></tr>))}</tbody>
          </table></div>}
          <p className="m-0 px-5 py-4 border-t border-faint text-ink2 max-w-[80ch]">{t('gov.breach.note')}</p>
        </Sheet>)}

      <Sheet title={t('gov.cap')} sub={t('gov.cap.sub')}>
        <div className="p-5 grid gap-4">
          {!user ? <p className="m-0">{t('gov.signin')}</p> : <div className="flex items-center gap-4 flex-wrap">
            <Btn disabled={benching} onClick={() => run(async () => { setBenching(true); setBench(null); try { setBench(await api('/benchmark?n=200')) } finally { setBenching(false) } })}>{benching && <Spinner />}{t('gov.cap.run')}</Btn>
            {benching && <span className="text-ink2">{t('gov.cap.wait')}</span>}</div>}
          {bench && (<>
            <dl className="m-0 grid grid-cols-2 sm:grid-cols-5 border-2 border-rule divide-x-2 divide-faint">{[[t('gov.cap.p50'), bench.p50_ms + ' ms'], [t('gov.cap.p95'), bench.p95_ms + ' ms'], [t('gov.cap.sec'), bench.per_second_one_worker], [t('gov.cap.day'), bench.per_day_one_worker.toLocaleString('en-IN')], [t('gov.cap.workers'), bench.workers_for_1m_per_day]].map(([k, v]) => (
              <div key={String(k)} className="px-4 py-3"><dt className="text-sm text-ink2">{k}</dt><dd className="m-0 num text-xl">{v}</dd></div>))}</dl>
            <p className="m-0 text-sm text-ink2 max-w-[80ch]">{bench.note}</p></>)}
        </div>
      </Sheet>

      {pol && (
        <Sheet title={t('gov.policy')} sub={t('gov.policy.sub', { v: pol.version, h: pol.hash })}>
          <div className="grid md:grid-cols-2 gap-x-10 p-5">
            <table className="chart"><thead><tr><th>{t('gov.params')}</th><th className="r">{t('gov.value')}</th></tr></thead><tbody>{Object.entries(pol.params).map(([k, v]) => <tr key={k}><td className="mono">{k}</td><td className="r num">{String(v)}</td></tr>)}</tbody></table>
            <table className="chart"><thead><tr><th>{t('gov.rules', { n: pol.rules.length })}</th></tr></thead><tbody>{pol.rules.map((r: J) => <tr key={r.id}><td>{r.title}</td></tr>)}</tbody></table>
          </div>
        </Sheet>)}
    </div>
  )
}
