import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Printer } from '@phosphor-icons/react'
import { api, adoptKeyFromHash, inr, type J } from '../api'
import { useI18n } from '../i18n'
import { Btn, Notice, Spinner } from '../components/kit'

/** "Other Most Important Terms and Conditions", laid out as RBI HFC Directions 2025 Annex IV, Appendix IV(b) (para 165).
 *  Facts that come from the case are filled in; everything only the lender can know is left visibly blank. */
export default function Mitc() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const [c, setC] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { if (id) adoptKeyFromHash(id); api('/cases/' + id).then(setC).catch(e => setErr(e.message)) }, [id])
  if (err) return <div className="p-6"><Notice tone="bad">{err}</Notice></div>
  if (!c) return <div className="p-6"><Spinner label={t('common.loading')} /></div>
  if (c.erased) return <div className="p-6"><Notice>{t('case.erased.b')}</Notice></div>
  const d = c.decision, k = d.kfs, p = c.property
  if (d.outcome !== 'APPROVE' || !k) return <div className="p-6"><Notice>{t('mitc.none')}</Notice><p><Link to={`/case/${c.case_id}`} className="underline text-blue font-display font-bold">{t('letter.back')}</Link></p></div>
  const blank = <span className="inline-block min-w-[14ch] border-b-2 border-rule align-baseline">&nbsp;<span className="sr-only">{t('mitc.blank')}</span></span>
  const rows: [string, ReactNode][] = [
    [t('mitc.1'), <>{t('mitc.1.v', { ptype: t('ap.pt.' + p.ptype), city: p.city, pin: p.pincode, area: p.area_sqft })} {p.encumbrance ? t('mitc.1.enc') : ''}</>],
    [t('mitc.2'), <>{t('mitc.lender')} {blank}</>],
    [t('mitc.3'), <>{t('mitc.3.v', { plan: p.approved_plan ? t('mitc.yes') : t('mitc.no'), title: p.litigation ? t('mitc.no') : t('mitc.yes') })} {t('mitc.lender')} {blank}</>],
    [t('mitc.4'), <>{t('mitc.4.v', { emi: inr(k.emi), n: k.tenure_months })} {t('mitc.4.due')} {blank}. {t('mitc.4.change')} {blank}</>],
    [t('mitc.5'), <>{t('mitc.5.v')} {blank}</>],
    [t('mitc.6'), <>{t('mitc.lender')} {blank}</>],
    [t('mitc.7'), <>{t('mitc.7.v')} {blank}</>],
  ]
  return (
    <div className="mx-auto max-w-[820px] px-5 py-6">
      <div className="no-print flex items-center justify-between gap-3 mb-5">
        <Link to={`/case/${c.case_id}`} className="inline-flex items-center gap-2 font-display font-semibold underline text-blue"><ArrowLeft size={18} weight="bold" aria-hidden />{t('letter.back')}</Link>
        <Btn onClick={() => window.print()}><Printer size={18} weight="bold" aria-hidden />{t('letter.print')}</Btn>
      </div>
      <div className="no-print mb-4"><Notice title={t('mitc.proto.t')}>{t('mitc.proto.b')}</Notice></div>
      <article className="letter sheet p-8 sm:p-10" lang={lang}>
        <header className="pb-4 border-b-2 border-rule flex items-start justify-between gap-6">
          <div><h1 className="m-0 text-2xl font-bold">{t('mitc.title')}</h1><p className="m-0 mt-1 text-sm text-ink2">{t('mitc.sub')}</p></div>
          <div className="text-right text-sm mono">{c.case_id}</div>
        </header>
        <p className="mt-4">{t('mitc.intro', { product: t(c.loan.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP'), borrower: c.applicant.name })}</p>
        <ol className="m-0 mt-2 pl-0 list-none grid gap-4">
          {rows.map(([h, v], i) => <li key={i}><h2 className="m-0 text-base font-bold">{i + 1}. {h}</h2><p className="m-0 mt-1">{v}</p></li>)}
        </ol>
        <p className="mt-6 text-sm">{t('mitc.agree')}</p>
        <div className="mt-8 grid grid-cols-2 gap-10 text-sm"><div className="pt-8 border-t-2 border-rule">{t('mitc.sig.b')}</div><div className="pt-8 border-t-2 border-rule">{t('mitc.sig.l')}</div></div>
        <footer className="mt-8 pt-3 border-t border-faint text-xs text-ink2 grid gap-1">
          <p className="m-0">{t('mitc.dup')}</p>
          <p className="m-0">{t('mitc.src')}</p>
        </footer>
      </article>
    </div>
  )
}
