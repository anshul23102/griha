import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Printer } from '@phosphor-icons/react'
import { api, inr, pct, type J, adoptKeyFromHash } from '../api'
import { useI18n } from '../i18n'
import { Btn, Notice, Spinner } from '../components/kit'

export default function Letter() {
  const { id } = useParams()
  const { t, tc, lang } = useI18n()
  const [c, setC] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { if (id) adoptKeyFromHash(id); api('/cases/' + id).then(setC).catch(e => setErr(e.message)) }, [id])
  if (err) return <div className="p-6"><Notice tone="bad">{err}</Notice></div>
  if (!c) return <div className="p-6"><Spinner label={t('common.loading')} /></div>
  if (c.erased) return <div className="p-6"><Notice>{t('case.erased.b')}</Notice></div>
  const d = c.decision, k = d.kfs
  const word = t(d.outcome === 'APPROVE' ? 'status.approved' : d.outcome === 'REFER' ? 'status.referred' : 'status.declined')
  const date = new Date().toLocaleDateString(lang === 'hi' ? 'hi-IN' : 'en-IN', { day: 'numeric', month: 'long', year: 'numeric' })
  return (
    <div className="mx-auto max-w-[820px] px-5 py-6">
      <div className="no-print flex items-center justify-between gap-3 mb-5">
        <Link to={`/case/${c.case_id}`} className="inline-flex items-center gap-2 font-display font-semibold underline text-blue"><ArrowLeft size={18} weight="bold" aria-hidden />{t('letter.back')}</Link>
        <Btn onClick={() => window.print()}><Printer size={18} weight="bold" aria-hidden />{t('letter.print')}</Btn>
      </div>
      <article className="letter sheet p-8 sm:p-10" lang={lang}>
        <header className="flex items-start justify-between gap-6 pb-5 border-b-2 border-rule">
          <div><div className="inline-flex items-center gap-2 bg-yellow text-black rounded-none px-2.5 py-1 font-display font-bold text-2xl leading-none"><span lang="hi">गृह</span><span>Griha</span></div>
            <p className="m-0 mt-2 text-sm text-ink2">{t('letter.tag')}</p></div>
          <div className="text-right text-sm"><div className="mono">{c.case_id}</div><div>{date}</div></div>
        </header>
        <h1 className="mt-6 text-3xl font-bold">{t('letter.title')}</h1>
        <p className="mt-4 mb-0">{t('letter.dear', { name: c.applicant.name })}</p>
        <p className="mt-3 mb-0">{t('letter.body', { product: t(c.loan.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP'), amount: inr(c.loan.amount) })}</p>
        <p className="mt-4 mb-0 font-display font-bold text-2xl border-2 border-rule inline-block px-4 py-1">{word}</p>
        <p className="mt-3">{d.headline}</p>
        {d.offer && k && (
          <>
            <h2 className="mt-6 text-xl font-semibold">{t('kfs.title')}</h2>
            <table className="chart"><tbody>{[[t('kfs.amount'), inr(k.loan_amount)], [t('kfs.tenure'), t('ap.years', { n: k.tenure_months / 12 })], [t('kfs.rate'), k.interest_rate_annual_pct + '%'], [t('kfs.emi'), inr(k.emi)], [t('kfs.fee'), inr(k.processing_fee)], [t('kfs.total'), inr(k.total_payable)], [t('kfs.apr'), k.apr_pct + '%']].map(([a, b]) => <tr key={a}><th scope="row">{a}</th><td className="r num">{b}</td></tr>)}</tbody></table>
            {k.other_disclosures && <ul className="m-0 mt-2 pl-5 grid gap-1 text-sm">{k.other_disclosures.map((x: J) => <li key={x.id}><strong>{x.label}:</strong> {x.value}{x.lender_to_set ? ` (${t('kfs.lender')})` : ''}</li>)}</ul>}
            <p className="text-sm mt-2">{k.foreclosure_charges}. {c.cooling_off_days ? t('kfs.cooling.v', { n: c.cooling_off_days }) : ''}</p>
          </>)}
        {d.reasons.length > 0 && (
          <>
            <h2 className="mt-6 text-xl font-semibold">{t('letter.reasons')}</h2>
            <ol className="m-0 mt-2 pl-5 grid gap-1.5">{d.reasons.filter((r: J) => r.direction !== 'favourable' && r.kind !== 'fraud' && r.code !== 'AML_SANCTIONS').slice(0, 6).map((r: J, i: number) => <li key={i}>{lang === 'hi' && tc(r.code) ? <><span lang="hi">{tc(r.code)}</span> <span className="text-sm text-ink2">({r.text})</span></> : r.text}</li>)}</ol>
          </>)}
        {d.pd && <p className="mt-5 text-sm">{t('case.pd', { p: pct(d.pd.pd), lo: pct(d.pd.pd_lo), hi: pct(d.pd.pd_hi) })}</p>}
        <footer className="mt-8 pt-4 border-t-2 border-rule text-xs text-ink2 grid gap-1">
          <p className="m-0">{t('letter.disclaimer')}</p>
          <p className="m-0 mono">policy v{d.policy_version} {d.policy_hash} · model {d.model_version}{c.audit[0] ? ` · audit ${c.audit[0].hash}` : ''}</p>
          <p className="m-0">{t('letter.grievance')}</p>
        </footer>
      </article>
    </div>
  )
}
