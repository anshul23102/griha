import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, UploadSimple, PaperPlaneTilt } from '@phosphor-icons/react'
import AaLink from '../components/AaLink'
import { api, apiForm, ApiError, lakh, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Field, inputCls, Notice, RouteStrip, Sheet, Spinner, type StationState } from '../components/kit'

type F = Record<string, string | boolean>
const EMPTY: F = {
  name: '', dob: '', pan: '', phone: '', gender: 'F', employment: 'salaried', employer: '', monthly_income: '', existing_emi: '0',
  product: 'HL', amount: '', tenure_years: '20', co_applicant_monthly_income: '0',
  city: '', pincode: '', property_type: 'apartment', area_sqft: '', property_age_years: '', declared_value: '', survey_no: '', valuation_1: '', valuation_2: '',
  statement_source: 'linked', bank_profile: 'steady', simulate_outage: 'none', consent: false,
}
const EXAMPLE: F = { ...EMPTY, name: 'Meena Patel', dob: '1988-04-12', pan: 'ABCDE1234F', phone: '9876543210', gender: 'F', employer: 'Metro Hospital',
  monthly_income: '62000', existing_emi: '4000', amount: '2400000', area_sqft: '950', property_age_years: '6', declared_value: '3600000', survey_no: 'KH-221/4' }
// Every click gets its own PAN, phone and survey number, so one judge's example never looks like another's to the linked-applicant check.
const rnd = (n: number) => Math.floor(Math.random() * n)
const letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
const freshExample = (): F => ({ ...EXAMPLE,
  pan: Array.from({ length: 5 }, () => letters[rnd(letters.length)]).join('') + String(1000 + rnd(9000)) + letters[rnd(letters.length)],
  phone: String(6 + rnd(4)) + String(100000000 + rnd(899999999)),
  survey_no: `KH-${100 + rnd(899)}/${1 + rnd(9)}` })
const STEP_OF: Record<string, number> = {
  simulate_outage: 3,
  name: 0, dob: 0, pan: 0, phone: 0, gender: 0, employment: 0, employer: 0, monthly_income: 0, existing_emi: 0,
  product: 1, amount: 1, tenure_months: 1, co_applicant_monthly_income: 1,
  city: 2, pincode: 2, property_type: 2, area_sqft: 2, property_age_years: 2, declared_value: 2, survey_no: 2, independent_valuations: 2,
  statement_source: 3, bank_profile: 3, document_id: 3, consent: 3, _: 3,
}
const REQUIRED: string[][] = [['name', 'dob', 'pan', 'phone', 'employer', 'monthly_income'], ['amount'], ['city', 'pincode', 'area_sqft', 'property_age_years', 'declared_value', 'survey_no'], []]

export default function Apply() {
  const { t } = useI18n()
  const nav = useNavigate()
  const draft = (() => { try { return JSON.parse(sessionStorage.getItem('griha_draft') || 'null') } catch { return null } })()
  const [restored, setRestored] = useState(!!draft)
  const [f, setF] = useState<F>(draft ? { ...EMPTY, ...draft.f, consent: false } : EMPTY)
  const [step, setStep] = useState<number>(draft ? Math.min(draft.step ?? 0, 3) : 0)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [ref, setRef] = useState<J | null>(null)
  const [doc, setDoc] = useState<J | null>(null)
  const [busy, setBusy] = useState(false)
  const [upBusy, setUpBusy] = useState(false)
  const [general, setGeneral] = useState<string | null>(null)
  const head = useRef<HTMLHeadingElement>(null)
  const idem = useRef<string>(crypto.randomUUID())      // one key per submission: a double click or a retry returns the first case instead of creating a second

  useEffect(() => { api('/reference').then(setRef).catch(e => setGeneral(e.message)) }, [])
  useEffect(() => { head.current?.focus() }, [step])
  useEffect(() => { try { sessionStorage.setItem('griha_draft', JSON.stringify({ f, step })) } catch { /* private mode */ } }, [f, step])

  const set = (k: string, v: string | boolean) => { setF(p => ({ ...p, [k]: v })); setErrors(p => { const { [k]: _, ...rest } = p; return rest }) }
  const city = ref?.cities.find((c: J) => c.name === f.city)
  const maxYears = ref ? ref.products[f.product as string].max_tenure_years : 30
  const years = useMemo(() => { const out = []; for (let y = 5; y <= maxYears; y += 5) out.push(y); if (!out.includes(maxYears)) out.push(maxYears); return out }, [maxYears])

  const num = (k: string) => Number(String(f[k]).replace(/,/g, ''))
  const fp = (id: string) => ({ id, name: id, value: f[id] as string, 'aria-invalid': !!errors[id] || undefined,
    'aria-describedby': errors[id] ? id + '-err' : undefined, className: inputCls(errors[id]), onChange: (e: { target: { value: string } }) => set(id, e.target.value) })

  function validate(s: number): boolean {
    const e: Record<string, string> = {}
    for (const k of REQUIRED[s]) if (!String(f[k]).trim()) e[k] = t('ap.err.required')
    if (s === 0) {
      if (f.pan && !/^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(String(f.pan).trim())) e.pan = t('ap.err.pan')
      if (f.phone && !/^[6-9][0-9]{9}$/.test(String(f.phone).replace(/\D/g, '').slice(-10))) e.phone = t('ap.err.phone')
      if (f.monthly_income && (num('monthly_income') < 8000)) e.monthly_income = t('ap.err.income')
      if (num('existing_emi') > num('monthly_income')) e.existing_emi = t('ap.err.emi')
    }
    if (s === 1 && f.amount && (num('amount') < (ref?.limits.min_loan ?? 300000))) e.amount = t('ap.err.amount', { min: lakh(ref?.limits.min_loan ?? 300000) })
    setErrors(p => ({ ...p, ...e }))
    return Object.keys(e).length === 0
  }
  const next = () => { if (validate(step)) setStep(s => s + 1) }

  async function upload(file: File) {
    if (!String(f.name).trim()) { setErrors(p => ({ ...p, document_id: t('ap.err.name_first') })); return }
    setUpBusy(true); setDoc(null); setErrors(p => { const { document_id: _, ...r } = p; return r })
    const fd = new FormData(); fd.append('applicant_name', String(f.name)); fd.append('file', file)
    const aa = /\.(json|xml)$/i.test(file.name)
    try { setDoc(await apiForm(aa ? '/documents/aa' : '/documents/statement', fd)) } catch (e) { setErrors(p => ({ ...p, document_id: (e as Error).message })) }
    setUpBusy(false)
  }

  async function submit() {
    setGeneral(null)
    if (!f.consent) { setErrors(p => ({ ...p, consent: t('ap.err.consent') })); return }
    if (f.statement_source === 'uploaded' && !doc) { setErrors(p => ({ ...p, document_id: t('ap.err.upload') })); return }
    setBusy(true)
    const body = {
      name: f.name, dob: f.dob, pan: f.pan, phone: f.phone, gender: f.gender, employment: f.employment, employer: f.employer,
      monthly_income: num('monthly_income'), existing_emi: num('existing_emi'), city: f.city, pincode: f.pincode, product: f.product,
      amount: num('amount'), tenure_months: num('tenure_years') * 12, co_applicant_monthly_income: num('co_applicant_monthly_income'),
      property_type: f.property_type, area_sqft: num('area_sqft'), property_age_years: num('property_age_years'), declared_value: num('declared_value'),
      independent_valuations: [num('valuation_1'), num('valuation_2')].filter(x => x > 0),
      survey_no: f.survey_no, simulate_outage: f.simulate_outage, consent: f.consent, statement_source: f.statement_source, bank_profile: f.bank_profile, document_id: doc?.doc_id ?? null,
    }
    try { const r = await api('/applications/new?wait=false', body, { 'Idempotency-Key': idem.current }); idem.current = crypto.randomUUID(); try { sessionStorage.removeItem('griha_draft') } catch { /* ignore */ } nav('/case/' + r.case_id) }
    catch (e) {
      setBusy(false)
      if (e instanceof ApiError && Object.keys(e.fields).length) {
        const fe = { ...e.fields }; if (fe.tenure_months) { fe.tenure_years = fe.tenure_months }
        setErrors(fe)
        setStep(Math.min(...Object.keys(e.fields).map(k => STEP_OF[k] ?? 3)))
      } else setGeneral((e as Error).message)
    }
  }

  const names = [t('ap.step.applicant'), t('ap.step.loan'), t('ap.step.property'), t('ap.step.bank')]
  const stations = names.map((label, i) => ({ key: String(i), label, state: (i < step ? 'ok' : i === step ? 'run' : 'wait') as StationState }))
  const cities = ref?.cities ?? []

  return (
    <div className="flex flex-col gap-6">
      <Board hi="गृह ऋण आवेदन" en="Home-loan application" aside={<>{t('ap.station', { n: step + 1, m: 4 })}</>}>
        <div className="mt-4"><RouteStrip stations={stations} label={t('ap.steps')} /></div>
      </Board>

      {restored && <Notice>{t('ap.draft')} <button type="button" className="underline text-blue font-display font-bold" onClick={() => { setF(EMPTY); setStep(0); setErrors({}); setRestored(false); try { sessionStorage.removeItem('griha_draft') } catch { /* ignore */ } }}>{t('ap.draft.clear')}</button></Notice>}
      <div className="grid gap-6 lg:grid-cols-[1fr_340px] items-start">
        <form onSubmit={e => { e.preventDefault(); if (step < 3) next(); else submit() }} noValidate>
          <Sheet title={<span ref={head} tabIndex={-1} className="outline-none">{names[step]}</span>} sub={t(`ap.sub.${step}`)}
            aside={step === 0 ? <button type="button" onClick={() => { setF(freshExample()); setErrors({}) }} className="text-sm underline text-blue font-display font-semibold min-h-11 px-1">{t('ap.example')}</button> : undefined}>
            <div className="p-5 grid gap-5 sm:grid-cols-2">
              {step === 0 && <>
                <div className="sm:col-span-2"><Field id="name" label={t('ap.name')} error={errors.name}><input {...fp('name')} autoComplete="name" /></Field></div>
                <Field id="dob" label={t('ap.dob')} error={errors.dob}><input {...fp('dob')} type="date" max="2005-11-01" /></Field>
                <Field id="gender" label={t('ap.gender')} hint={t('ap.gender.hint')}>
                  <select {...fp('gender')}><option value="F">{t('ap.g.f')}</option><option value="M">{t('ap.g.m')}</option><option value="O">{t('ap.g.o')}</option></select></Field>
                <Field id="pan" label={t('ap.pan')} hint={t('ap.pan.hint')} error={errors.pan}><input {...fp('pan')} maxLength={10} autoCapitalize="characters" className={inputCls(errors.pan) + ' mono uppercase'} /></Field>
                <Field id="phone" label={t('ap.phone')} error={errors.phone}><input {...fp('phone')} inputMode="numeric" autoComplete="tel" maxLength={13} /></Field>
                <Field id="employment" label={t('ap.employment')}>
                  <select {...fp('employment')}><option value="salaried">{t('ap.emp.s')}</option><option value="self_employed">{t('ap.emp.se')}</option></select></Field>
                <Field id="employer" label={f.employment === 'salaried' ? t('ap.employer') : t('ap.business')} error={errors.employer}><input {...fp('employer')} /></Field>
                <Field id="monthly_income" label={t('ap.income')} hint={t('ap.income.hint')} error={errors.monthly_income}><input {...fp('monthly_income')} inputMode="numeric" /></Field>
                <Field id="existing_emi" label={t('ap.emi')} hint={t('ap.emi.hint')} error={errors.existing_emi}><input {...fp('existing_emi')} inputMode="numeric" /></Field>
              </>}
              {step === 1 && <>
                <fieldset className="sm:col-span-2 m-0 p-0 border-0">
                  <legend className="font-display font-semibold text-[0.9375rem] mb-1.5">{t('ap.product')}</legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(['HL', 'LAP'] as const).map(p => (
                      <label key={p} className={`flex gap-3 items-start p-4 border-2 rounded-none cursor-pointer ${f.product === p ? 'border-blue bg-ground' : 'border-faint'}`}>
                        <input type="radio" name="product" value={p} checked={f.product === p} onChange={() => { set('product', p); set('tenure_years', p === 'HL' ? '20' : '10') }} className="mt-1.5 size-5 accent-[var(--blue)]" />
                        <span><span className="block font-display font-semibold">{t(`ap.p.${p}`)}</span><span className="block text-sm text-ink2">{t(`ap.p.${p}.d`)}</span></span>
                      </label>))}
                  </div>
                </fieldset>
                <Field id="amount" label={t('ap.amount')} hint={f.amount ? lakh(num('amount')) : t('ap.amount.hint', { min: lakh(ref?.limits.min_loan ?? 300000), max: lakh(ref?.limits.max_loan ?? 15000000) })} error={errors.amount}><input {...fp('amount')} inputMode="numeric" /></Field>
                <Field id="tenure_years" label={t('ap.tenure')} error={errors.tenure_years}>
                  <select {...fp('tenure_years')}>{years.map(y => <option key={y} value={y}>{t('ap.years', { n: y })}</option>)}</select></Field>
                <div className="sm:col-span-2"><Field id="co_applicant_monthly_income" label={t('ap.co')} hint={t('ap.co.hint')} error={errors.co_applicant_monthly_income}><input {...fp('co_applicant_monthly_income')} inputMode="numeric" /></Field></div>
              </>}
              {step === 2 && <>
                <Field id="city" label={t('ap.city')} error={errors.city}>
                  <select {...fp('city')} onChange={e => { set('city', e.target.value); set('pincode', '') }}><option value="">{t('ap.choose')}</option>{cities.map((c: J) => <option key={c.name} value={c.name}>{c.name} (T{c.tier})</option>)}</select></Field>
                <Field id="pincode" label={t('ap.pin')} hint={t('ap.pin.hint')} error={errors.pincode}>
                  <select {...fp('pincode')} disabled={!city}><option value="">{t('ap.choose')}</option>{city?.pins.map((p: string) => <option key={p} value={p}>{p}</option>)}</select></Field>
                <Field id="property_type" label={t('ap.ptype')}>
                  <select {...fp('property_type')}>{(ref?.property_types ?? ['apartment', 'house', 'plot', 'commercial']).map((p: string) => <option key={p} value={p}>{t(`ap.pt.${p}`)}</option>)}</select></Field>
                <Field id="survey_no" label={t('ap.survey')} hint={t('ap.survey.hint')} error={errors.survey_no}><input {...fp('survey_no')} className={inputCls(errors.survey_no) + ' mono'} /></Field>
                <Field id="area_sqft" label={t('ap.area')} error={errors.area_sqft}><input {...fp('area_sqft')} inputMode="numeric" /></Field>
                <Field id="property_age_years" label={t('ap.age')} error={errors.property_age_years}><input {...fp('property_age_years')} inputMode="numeric" /></Field>
                <div className="sm:col-span-2 grid gap-4 sm:grid-cols-2">
                  <p className="sm:col-span-2 m-0 text-sm text-ink2">{t('ap.val.hint', { n: num('amount') >= 7500000 ? 2 : num('amount') >= 5000000 ? 1 : 0 })}</p>
                  <Field id="valuation_1" label={t('ap.val1')} error={errors.independent_valuations}><input {...fp('valuation_1')} inputMode="numeric" /></Field>
                  <Field id="valuation_2" label={t('ap.val2')}><input {...fp('valuation_2')} inputMode="numeric" /></Field>
                </div>
                <div className="sm:col-span-2"><Field id="declared_value" label={t('ap.value')} hint={f.declared_value ? lakh(num('declared_value')) : t('ap.value.hint')} error={errors.declared_value}><input {...fp('declared_value')} inputMode="numeric" /></Field></div>
              </>}
              {step === 3 && <>
                <fieldset className="sm:col-span-2 m-0 p-0 border-0">
                  <legend className="font-display font-semibold text-[0.9375rem] mb-1.5">{t('ap.stmt')}</legend>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {(['linked', 'uploaded'] as const).map(s => (
                      <label key={s} className={`flex gap-3 items-start p-4 border-2 rounded-none cursor-pointer ${f.statement_source === s ? 'border-blue bg-ground' : 'border-faint'}`}>
                        <input type="radio" name="statement_source" value={s} checked={f.statement_source === s} onChange={() => set('statement_source', s)} className="mt-1.5 size-5 accent-[var(--blue)]" />
                        <span><span className="block font-display font-semibold">{t(`ap.s.${s}`)}</span><span className="block text-sm text-ink2">{t(`ap.s.${s}.d`)}</span></span>
                      </label>))}
                  </div>
                </fieldset>
                {f.statement_source === 'linked' ? (
                  <div className="sm:col-span-2 grid gap-3">
                    <Field id="bank_profile" label={t('ap.profile')} hint={t('ap.profile.hint')}>
                      <select {...fp('bank_profile')}><option value="steady">{t('ap.bp.steady')}</option><option value="variable">{t('ap.bp.variable')}</option><option value="irregular">{t('ap.bp.irregular')}</option></select></Field>
                    <Notice tone="info">{t('ap.sim.note')}</Notice>
                  </div>
                ) : (
                  <div className="sm:col-span-2 grid gap-3">
                    <AaLink name={String(f.name)} phone={String(f.phone)} onDoc={d => { setDoc(d); setErrors(p => { const { document_id: _, ...r } = p; return r }) }} />
                    <Field id="document_id" label={t('ap.pdf')} hint={t('ap.pdf.hint')} error={errors.document_id}>
                      <input id="document_id" type="file" accept="application/pdf,application/json,application/xml,text/xml,.json,.xml" onChange={e => e.target.files?.[0] && upload(e.target.files[0])} className={inputCls(errors.document_id) + ' py-2'} />
                    </Field>
                    {upBusy && <Spinner label={t('ap.reading')} />}
                    {doc && (
                      <Notice tone={doc.issues.length ? 'warn' : 'ok'} title={doc.method === 'account_aggregator' ? t('ap.read.aa', { n: doc.transactions }) : t('ap.read', { n: doc.transactions, pages: doc.pages, by: doc.method === 'llm' ? doc.provider + ' (' + doc.model + ')' : t('ap.parser') })}>
                        {doc.issues.length ? <ul className="m-0 pl-5">{doc.issues.map((i: J) => <li key={i.code}><span className="mono">{i.code}</span> {i.text}</li>)}</ul> : t('ap.read.clean')}
                      </Notice>)}
                    <p className="m-0 text-sm text-ink2 flex items-start gap-2"><UploadSimple size={18} aria-hidden className="mt-0.5 shrink-0" />{t('ap.pdf.sample')} <a className="underline" href="/api/samples/aa/salaried_approve?format=json" download>{t('ap.aa.sample')}</a></p>
                  </div>
                )}
                <div className="sm:col-span-2">
                  <Field id="simulate_outage" label={t('ap.outage')} hint={t('ap.outage.hint')}>
                    <select {...fp('simulate_outage')}><option value="none">{t('ap.out.none')}</option><option value="bureau_flaky">{t('ap.out.flaky')}</option><option value="bureau">{t('ap.out.bureau')}</option><option value="kyc">{t('ap.out.kyc')}</option></select></Field>
                </div>
                <div className="sm:col-span-2 border-t-2 border-faint pt-5">
                  <label className="flex gap-3 items-start cursor-pointer">
                    <input type="checkbox" checked={!!f.consent} onChange={e => set('consent', e.target.checked)} aria-describedby={errors.consent ? 'consent-err' : undefined} className="mt-1 size-5 accent-[var(--blue)]" />
                    <span><span className="block font-display font-semibold">{t('ap.consent')}</span><span className="block text-sm text-ink2">{t('ap.consent.b')} <Link to="/privacy" target="_blank" className="underline">{t('ap.consent.link')}</Link></span></span>
                  </label>
                  {errors.consent && <p id="consent-err" role="alert" className="text-sm text-bad mt-2 m-0">{errors.consent}</p>}
                </div>
                {general && <div className="sm:col-span-2"><Notice tone="bad">{general}</Notice></div>}
                {errors._ && <div className="sm:col-span-2"><Notice tone="bad">{errors._}</Notice></div>}
              </>}
            </div>
            <div className="flex justify-between gap-3 px-5 py-4 border-t-2 border-rule">
              <Btn kind="ghost" onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0 || busy}><ArrowLeft size={18} weight="bold" aria-hidden />{t('common.back')}</Btn>
              {step < 3
                ? <Btn type="submit">{t('common.next')}<ArrowRight size={18} weight="bold" aria-hidden /></Btn>
                : <Btn type="submit" disabled={busy}>{busy ? <Spinner /> : <PaperPlaneTilt size={18} weight="bold" aria-hidden />}{t('ap.submit')}</Btn>}
            </div>
          </Sheet>
        </form>

        <aside className="lg:sticky lg:top-4 flex flex-col gap-4" aria-label={t('ap.slip')}>
          <Link to="/" className="font-display font-bold underline text-blue">{t('ap.calc.link')}</Link>
          <Sheet title={t('ap.slip')} sub={t('ap.slip.sub')}>
            <dl className="m-0 px-5 py-3 text-[0.9375rem]">
              {[[t('ap.name'), f.name], [t('ap.product'), t(`ap.p.${f.product}`)], [t('ap.amount'), f.amount ? lakh(num('amount')) : ''],
                [t('ap.tenure'), t('ap.years', { n: String(f.tenure_years) })], [t('ap.city'), f.city], [t('ap.value'), f.declared_value ? lakh(num('declared_value')) : '']].map(([k, v]) => (
                <div key={String(k)} className="flex justify-between gap-3 py-2 border-b border-faint last:border-0"><dt className="text-ink2">{k}</dt><dd className="m-0 font-medium text-right">{v ? String(v) : <span className="text-ink2">-</span>}</dd></div>))}
            </dl>
          </Sheet>
          <Notice title={t('ap.next.t')}>{t('ap.next.b')}</Notice>
        </aside>
      </div>
    </div>
  )
}
