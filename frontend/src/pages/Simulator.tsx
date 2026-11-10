import { useEffect, useState } from 'react'
import { ArrowDown, ArrowUp, Minus } from '@phosphor-icons/react'
import { api, session, pct, type J } from '../api'
import { useI18n } from '../i18n'
import Login from '../components/Login'
import { Board, Btn, Notice, Sheet, Spinner, StatusWord } from '../components/kit'

const KNOBS = [
  { key: 'foir_cap', min: 0.4, max: 0.75, step: 0.01, fmt: (v: number) => pct(v, 0) },
  { key: 'pd_approve_max', min: 0.02, max: 0.15, step: 0.005, fmt: (v: number) => pct(v) },
  { key: 'pd_reject_min', min: 0.1, max: 0.5, step: 0.01, fmt: (v: number) => pct(v, 0) },
  { key: 'min_eligibility_ratio', min: 0.3, max: 1, step: 0.05, fmt: (v: number) => pct(v, 0) },
]

const Row = ({ label, a, c, f, upGood }: { label: string; a: number; c: number; f: (v: number) => string; upGood: boolean | null }) => {
  const d = c - a, flat = Math.abs(d) < 1e-9
  const good = upGood === null ? null : (d > 0) === upGood
  return (
    <tr><th scope="row">{label}</th><td className="r num">{f(a)}</td><td className="r num font-semibold">{f(c)}</td>
      <td className={`r num font-display font-semibold ${flat || good === null ? 'text-ink2' : good ? 'text-ok' : 'text-bad'}`}>
        <span className="inline-flex items-center gap-1">{flat ? <Minus size={14} weight="bold" aria-hidden /> : d > 0 ? <ArrowUp size={14} weight="bold" aria-hidden /> : <ArrowDown size={14} weight="bold" aria-hidden />}{f(Math.abs(d))}</span></td></tr>)
}

export default function Simulator() {
  const { t } = useI18n()
  const [user, setUser] = useState(session())
  const [base, setBase] = useState<J | null>(null)
  const [vals, setVals] = useState<Record<string, number>>({})
  const [res, setRes] = useState<J | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { const h = () => setUser(session()); window.addEventListener('griha-auth', h); return () => window.removeEventListener('griha-auth', h) }, [])
  useEffect(() => { api('/policy').then(p => { setBase(p); setVals(Object.fromEntries(KNOBS.map(k => [k.key, p.params[k.key]]))) }).catch(e => setErr(e.message)) }, [])
  if (!user) return <Login hi="नीति सिम्युलेटर" en="Policy simulator" />

  const changed = KNOBS.filter(k => base && Math.abs(vals[k.key] - base.params[k.key]) > 1e-9)
  async function run() {
    setBusy(true); setErr(null)
    try { setRes(await api('/simulate', { changes: Object.fromEntries(changed.map(k => ['params.' + k.key, vals[k.key]])) })) } catch (e) { setErr((e as Error).message) }
    setBusy(false)
  }

  return (
    <div className="flex flex-col gap-6">
      <Board hi="नीति सिम्युलेटर" en="Policy simulator" aside={base ? <>policy v{base.version}<br />{base.hash}</> : undefined}>
        <p className="m-0 mt-2 font-medium max-w-[62ch]">{t('sim.lead')}</p>
      </Board>
      <div className="grid gap-6 lg:grid-cols-[380px_1fr] items-start">
        <Sheet title={t('sim.thresholds')} sub={t('sim.thresholds.sub')}>
          <div className="p-5 grid gap-6">
            {base && KNOBS.map(k => (
              <div key={k.key}>
                <label htmlFor={k.key} className="flex justify-between gap-3 font-display font-semibold"><span>{t('sim.k.' + k.key)}</span>
                  <span className="num">{k.fmt(vals[k.key] ?? 0)}</span></label>
                <input id={k.key} type="range" min={k.min} max={k.max} step={k.step} value={vals[k.key] ?? 0} onChange={e => setVals(v => ({ ...v, [k.key]: +e.target.value }))} className="w-full mt-2 accent-[var(--blue)] h-6" />
                <p className="m-0 text-sm text-ink2">{t('sim.current')} <span className="num">{k.fmt(base.params[k.key])}</span>{Math.abs(vals[k.key] - base.params[k.key]) > 1e-9 && <> · <b>{t('sim.changed')}</b></>}</p>
              </div>))}
            <div className="flex items-center gap-3 flex-wrap">
              <Btn onClick={run} disabled={busy || !changed.length}>{busy && <Spinner />}{t('sim.run')}</Btn>
              <Btn kind="ghost" onClick={() => base && setVals(Object.fromEntries(KNOBS.map(k => [k.key, base.params[k.key]])))} disabled={!changed.length || busy}>{t('sim.reset')}</Btn>
            </div>
            {busy && <p className="m-0 text-sm text-ink2">{t('sim.wait')}</p>}
            {!changed.length && <p className="m-0 text-sm text-ink2">{t('sim.move')}</p>}
            {err && <Notice tone="bad">{err}</Notice>}
          </div>
        </Sheet>
        {res ? <Results r={res} /> : <Notice>{t('sim.empty')}</Notice>}
      </div>
    </div>
  )
}

function Results({ r }: { r: J }) {
  const { t } = useI18n()
  const b = r.baseline, s = r.scenario
  const cr = (v: number) => '₹' + (v / 1e7).toFixed(1) + ' Cr'
  return (
    <div className="flex flex-col gap-6">
      <Sheet title={t('sim.impact')} sub={t('sim.flipped', { n: r.flipped, total: b.n })}>
        <table className="chart"><thead><tr><th>{t('sim.metric')}</th><th className="r">{t('sim.cur')}</th><th className="r">{t('sim.prop')}</th><th className="r">{t('sim.delta')}</th></tr></thead><tbody>
          <Row label={t('sim.m.approve')} a={b.approve_rate} c={s.approve_rate} f={v => pct(v)} upGood />
          <Row label={t('sim.m.refer')} a={b.refer_rate} c={s.refer_rate} f={v => pct(v)} upGood={false} />
          <Row label={t('sim.m.reject')} a={b.reject_rate} c={s.reject_rate} f={v => pct(v)} upGood={null} />
          <Row label={t('sim.m.volume')} a={b.approved_volume} c={s.approved_volume} f={cr} upGood />
          <Row label={t('sim.m.el')} a={b.expected_loss_pct} c={s.expected_loss_pct} f={v => pct(v, 2)} upGood={false} />
          <Row label={t('sim.m.real')} a={b.realised_default_rate_approved} c={s.realised_default_rate_approved} f={v => pct(v, 2)} upGood={false} />
        </tbody></table>
      </Sheet>
      {r.flipped_examples.length > 0 && (
        <Sheet title={t('sim.examples')}>
          <table className="chart"><tbody>{r.flipped_examples.map((e: J) => <tr key={e.case_id}><th scope="row" className="mono">{e.case_id}</th><td><StatusWord o={e.from} /></td><td aria-hidden>→</td><td><StatusWord o={e.to} /></td></tr>)}</tbody></table>
        </Sheet>)}
      <Sheet title={t('sim.fair')} sub={t('sim.fair.sub')}>
        <table className="chart"><tbody>{Object.entries(s.approval_rate_by_group).map(([k, v]) => <tr key={k}><th scope="row">{t('grp.' + k)}</th><td className="r num">{pct(v as number, 0)}</td></tr>)}</tbody></table>
        <table className="chart"><tbody>{(s.fairness ?? []).map((x: J) => (
          <tr key={x.attribute}><th scope="row">{t('sim.air')} · {t('grp.attr.' + x.attribute)}</th>
            <td className="r num"><b className={x.flag === 'below_80_significant' ? 'text-bad' : x.flag === 'ok' ? 'text-ok' : 'text-wait'}>{x.ratio}</b> <span className="text-ink2">[{x.ci95[0]} – {x.ci95[1]}]</span></td>
            <td className="text-sm text-ink2">{t('sim.flag.' + x.flag)}</td></tr>))}</tbody></table>
        <p className="m-0 px-5 pb-4 text-sm text-ink2">{t('sim.fair.note')}</p>
      </Sheet>
    </div>
  )
}
