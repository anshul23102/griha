import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Play } from '@phosphor-icons/react'
import { api, type J } from '../api'
import { useI18n, headlineOf } from '../i18n'
import { STAGES, ST } from '../stages'
import { Btn, Flap, Notice, RouteStrip, Sheet, Spinner, statusCls, type Outcome, type StationState } from './kit'
import { useCase } from '../useCase'

const CASES = [['salaried_approve', 'demo.approve'], ['fraud_edit', 'demo.fraud'], ['sanctions', 'demo.sanction']] as const

export default function LiveDemo({ onRun }: { onRun?: () => void }) {
  const { t, tc, lang } = useI18n()
  const [pick, setPick] = useState<string>(CASES[0][0])
  const [cid, setCid] = useState<string | undefined>(undefined)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const { c, prog, err: caseErr } = useCase(cid)
  useEffect(() => { if (c) onRun?.() }, [c?.case_id])

  async function run() {
    setBusy(true); setErr(null); setCid(undefined)
    try { setCid((await api('/applications?wait=false', { scenario_id: pick })).case_id) } catch (e) { setErr((e as Error).message) }
    setBusy(false)
  }
  const ev: J[] = c ? c.decision.evidence : (prog?.stages ?? [])
  const stations: { key: string; label: string; ms?: number; state: StationState }[] = STAGES.map((s, i) => {
    const hit = ev.find((e: J) => e.stage === s)
    return { key: s, label: t('stage.' + s), ms: hit?.ms, state: (hit ? ST[hit.status] : !c && i === ev.length ? 'run' : 'wait') as StationState }
  })
  const d = c?.decision
  const o = d?.outcome as Outcome | undefined
  const word = o ? t(o === 'APPROVE' ? 'status.approved' : o === 'REFER' ? 'status.referred' : 'status.declined') : ''

  return (
    <Sheet title={t('demo.title')} sub={t('demo.sub')}>
      <div className="p-5 grid gap-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="demo-pick" className="font-display font-semibold text-[0.9375rem]">{t('demo.pick')}</label>
            <select id="demo-pick" value={pick} onChange={e => setPick(e.target.value)} className="w-full min-h-11 mt-1.5 px-3 bg-sheet text-ink border-2 border-rule rounded-none">
              {CASES.map(([id, k]) => <option key={id} value={id}>{t(k)}</option>)}
            </select>
          </div>
          <Btn onClick={run} disabled={busy}>{busy ? <Spinner /> : <Play size={18} weight="fill" aria-hidden />}{t('demo.run')}</Btn>
        </div>
        {(err || caseErr) && <Notice tone="bad">{err || caseErr}</Notice>}
        {!cid && !busy && <p className="m-0 text-ink2">{t('demo.idle')}</p>}
        {cid && (
          <div className="grid gap-4">
            <div className="bg-yellow border-[3px] border-black p-4"><RouteStrip stations={stations} label={t('case.route')} /></div>
            {c && o && (
              <div className="grid gap-3">
                <div className={statusCls(o)}><Flap word={lang === 'en' ? word.toUpperCase() : word} /></div>
                <p className="m-0 font-medium">{headlineOf(d, t, tc, lang)}</p>
                <dl className="m-0 flex flex-wrap gap-x-8 gap-y-2">
                  {d.pd && <div><dt className="text-sm text-ink2">{t('demo.score')}</dt><dd className="m-0 num text-xl">{d.pd.score} <span className="text-base">({t('ev.score.band', { b: d.pd.band })})</span></dd></div>}
                  {d.offer && <div><dt className="text-sm text-ink2">{t('demo.rate')}</dt><dd className="m-0 num text-xl">{d.offer.rate_pct}%</dd></div>}
                  <div><dt className="text-sm text-ink2">{t('demo.time')}</dt><dd className="m-0 num text-xl">{ev.reduce((a: number, e: J) => a + e.ms, 0).toFixed(0)} ms</dd></div>
                </dl>
                <Link to={'/case/' + c.case_id} className="inline-flex items-center gap-2 font-display font-bold underline text-blue">{t('demo.open')}<ArrowRight size={18} weight="bold" aria-hidden /></Link>
              </div>
            )}
          </div>
        )}
      </div>
    </Sheet>
  )
}
