import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from '@phosphor-icons/react'
import { api, inr, lakh, pct, type J } from '../api'
import { useI18n } from '../i18n'
import { Field, inputCls, Sheet } from './kit'

export default function EligibilityCalc() {
  const { t } = useI18n()
  const [v, setV] = useState({ product: 'HL', income: '60000', emi: '5000', value: '3500000', years: '20' })
  const [r, setR] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const set = (k: string, x: string) => setV(p => ({ ...p, [k]: x }))
  useEffect(() => {
    const id = setTimeout(() => {
      const income = Number(v.income), emi = Number(v.emi), value = Number(v.value)
      if (!(income >= 8000) || !(value >= 100000) || emi > income) { setR(null); setErr(emi > income ? t('ap.err.emi') : t('ap.err.required')); return }
      setErr(null)
      api('/eligibility', { product: v.product, monthly_income: income, existing_emi: emi, tenure_years: Number(v.years), property_value: value })
        .then(setR).catch(e => setErr(e.message))
    }, 300)
    return () => clearTimeout(id)
  }, [v])
  const max = v.product === 'HL' ? 30 : 15
  const years = Array.from({ length: max / 5 }, (_, i) => (i + 1) * 5)
  return (
    <Sheet title={t('calc.title')} sub={t('calc.sub')}>
      <div className="p-5 grid gap-5 sm:grid-cols-2">
        <fieldset className="sm:col-span-2 m-0 p-0 border-0 flex gap-2">
          <legend className="sr-only">{t('ap.product')}</legend>
          {(['HL', 'LAP'] as const).map(p => (
            <button key={p} type="button" aria-pressed={v.product === p} onClick={() => { set('product', p); if (Number(v.years) > (p === 'HL' ? 30 : 15)) set('years', '15') }}
              className={`min-h-11 px-4 border-2 font-display font-bold ${v.product === p ? 'bg-ink text-sheet border-ink' : 'border-rule hover:bg-ground'}`}>{t('ap.p.' + p)}</button>))}
        </fieldset>
        <Field id="c-income" label={t('calc.income')}><input id="c-income" inputMode="numeric" value={v.income} onChange={e => set('income', e.target.value)} className={inputCls()} /></Field>
        <Field id="c-emi" label={t('calc.emi')}><input id="c-emi" inputMode="numeric" value={v.emi} onChange={e => set('emi', e.target.value)} className={inputCls()} /></Field>
        <Field id="c-value" label={t('calc.value')}><input id="c-value" inputMode="numeric" value={v.value} onChange={e => set('value', e.target.value)} className={inputCls()} /></Field>
        <Field id="c-years" label={t('calc.tenure')}>
          <select id="c-years" value={v.years} onChange={e => set('years', e.target.value)} className={inputCls()}>{years.map(y => <option key={y} value={y}>{t('ap.years', { n: y })}</option>)}</select></Field>
      </div>
      <div className="border-t-2 border-rule p-5" aria-live="polite">
        {err && !r ? <p className="m-0 text-bad">{err}</p> : r && (
          r.eligible ? (
            <div className="grid gap-2">
              <p className="m-0 text-ink2">{t('calc.max')}</p>
              <p className="m-0 num text-[2.5rem] leading-none font-medium">{lakh(r.max_loan)}</p>
              <p className="m-0">{t('calc.bind.' + r.binding, { ltv: pct(r.ltv_cap, 0) })}</p>
              <p className="m-0 text-ink2 text-[0.9375rem]">{t('calc.emi.range', { lo: r.rate_range_pct[0], hi: r.rate_range_pct[1] })}: <span className="num">{inr(r.emi_range[0])} – {inr(r.emi_range[1])}</span></p>
              <p className="m-0 text-ink2 text-sm">{t('calc.stress', { r: r.stress_rate_pct })}. {r.note}</p>
              <Link to="/apply" className="inline-flex items-center gap-2 font-display font-bold underline text-blue mt-1">{t('calc.go')}<ArrowRight size={18} weight="bold" aria-hidden /></Link>
            </div>) : <p className="m-0 text-wait font-medium">{t('calc.not', { min: lakh(r.min_loan) })}</p>)}
      </div>
    </Sheet>
  )
}
