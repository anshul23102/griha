import { useEffect, useState } from 'react'
import { api, inr, pct, type J } from '../api'
import { useI18n } from '../i18n'
import { Field, Notice, Sheet, Spinner } from './kit'

/** Business impact. Measured figures come from the live engine over synthetic cases; time and cost are assumptions the viewer can change. */
export default function Impact() {
  const { t } = useI18n()
  const [a, setA] = useState({ manual_minutes: '45', review_minutes: '20', cost_per_hour: '500', files_per_month: '1000' })
  const [d, setD] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    const id = setTimeout(() => {
      const q = new URLSearchParams(Object.entries(a).map(([k, v]) => [k, String(Number(v) || 0)])).toString()
      api('/impact?' + q).then(x => { setD(x); setErr(null) }).catch(e => setErr(e.message))
    }, 250)
    return () => clearTimeout(id)
  }, [a])
  const set = (k: keyof typeof a) => ({ id: 'imp_' + k, value: a[k], inputMode: 'numeric' as const, onChange: (e: { target: { value: string } }) => setA(p => ({ ...p, [k]: e.target.value.replace(/[^0-9.]/g, '') })) })
  const m = d?.measured, k = d?.computed
  const tag = (kind: 'measured' | 'assumed') => <span className={'font-display font-bold text-xs px-1.5 py-0.5 border-2 ' + (kind === 'measured' ? 'border-ok text-ok' : 'border-wait text-wait')}>{t('imp.' + kind)}</span>
  return (
    <Sheet title={t('imp.title')} sub={t('imp.sub')}>
      <div className="p-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field id="imp_manual_minutes" label={t('imp.f.manual')}><input {...set('manual_minutes')} /></Field>
        <Field id="imp_review_minutes" label={t('imp.f.review')}><input {...set('review_minutes')} /></Field>
        <Field id="imp_cost_per_hour" label={t('imp.f.cost')}><input {...set('cost_per_hour')} /></Field>
        <Field id="imp_files_per_month" label={t('imp.f.files')}><input {...set('files_per_month')} /></Field>
      </div>
      {err && <div className="px-5 pb-4"><Notice tone="bad">{err}</Notice></div>}
      {!d ? <div className="p-5"><Spinner label={t('common.loading')} /></div> : (
        <div className="overflow-x-auto"><table className="chart min-w-[560px]"><tbody>
          <tr><th scope="row" className="font-normal">{t('imp.r.stp')}</th><td className="r num">{pct(m.straight_through_rate, 0)}</td><td>{tag('measured')}</td><td className="text-ink2 text-sm">{t('imp.r.stp.n', { a: pct(m.approve_rate, 0), r: pct(m.reject_rate, 0), f: pct(m.refer_rate, 0) })}</td></tr>
          <tr><th scope="row" className="font-normal">{t('imp.r.ms')}</th><td className="r num">{m.engine_ms_median} ms</td><td>{tag('measured')}</td><td className="text-ink2 text-sm">{t('imp.r.ms.n', { p: m.engine_ms_p95 })}</td></tr>
          <tr><th scope="row" className="font-normal">{t('imp.r.min')}</th><td className="r num">{k.officer_minutes_per_file_manual} → {k.officer_minutes_per_file_with_engine}</td><td>{tag('assumed')}</td><td className="text-ink2 text-sm">{t('imp.r.min.n')}</td></tr>
          <tr><th scope="row" className="font-normal">{t('imp.r.cost')}</th><td className="r num">{inr(k.cost_per_file_manual_inr)} → {inr(k.cost_per_file_with_engine_inr)}</td><td>{tag('assumed')}</td><td className="text-ink2 text-sm">{t('imp.r.cost.n')}</td></tr>
          <tr><th scope="row" className="font-bold">{t('imp.r.hours')}</th><td className="r num font-bold">{Math.round(k.officer_hours_saved_per_month).toLocaleString('en-IN')} h</td><td>{tag('assumed')}</td><td className="text-ink2 text-sm">{t('imp.r.hours.n', { p: pct(k.share_of_officer_time_saved, 0) })}</td></tr>
          <tr><th scope="row" className="font-bold">{t('imp.r.save')}</th><td className="r num font-bold">{inr(k.cost_saved_per_month_inr)}</td><td>{tag('assumed')}</td><td className="text-ink2 text-sm">{t('imp.r.save.n')}</td></tr>
        </tbody></table></div>)}
      {d && m.refer_breakdown && (
        <div className="px-5 py-4 border-t border-faint grid gap-2">
          <h3 className="m-0 text-base font-bold">{t('imp.humans')}</h3>
          <p className="m-0 text-sm text-ink2 max-w-[80ch]">{t('imp.humans.sub')}</p>
          <ul className="m-0 pl-5 grid gap-1 text-sm">
            {Object.entries(m.refer_breakdown.by_queue).map(([q, v]) => <li key={q}><b>{t('queue.' + q)}</b>: <span className="num">{pct(v as number, 1)}</span>{q === 'CREDIT' && <> ({Object.entries(m.refer_breakdown.credit_reasons).map(([r, x]) => `${t('imp.cr.' + r)} ${pct(x as number, 1)}`).join(', ')})</>}</li>)}
          </ul>
        </div>)}
      <p className="m-0 px-5 py-3 text-sm text-ink2 border-t border-faint">{d ? t('imp.note', { src: m.source }) : ''} {t('imp.disclaimer')}</p>
    </Sheet>
  )
}
