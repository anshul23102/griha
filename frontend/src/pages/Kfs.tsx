import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Printer } from '@phosphor-icons/react'
import { api, adoptKeyFromHash, inr, type J } from '../api'
import { useI18n } from '../i18n'
import { Btn, Notice, Spinner } from '../components/kit'

// The Key Facts Statement in the standardised format of the NBFC Responsible Business Conduct Directions 2025, Annex I (para 29):
// Part 1 interest rate and fees, Part 2 qualitative information, the APR computation sheet and the amortisation schedule.
// Wording of items that only the lender can know is shown as "Lender to state" and is never invented.
const T = {
  en: { title: 'Key Facts Statement', sub: 'Format: RBI (NBFC - Responsible Business Conduct) Directions, 2025, Annex I', p1: 'Part 1: Interest rate and fees and charges', p2: 'Part 2: Other qualitative information',
    apr: 'Computation of the annual percentage rate (APR)', sch: 'Repayment schedule', prop: 'Proposal number', valid: 'Open for acceptance until', validb: 'At least three working days. The lender is bound by these terms if you accept in this time.',
    ack: 'I have read this statement, its contents were explained to me, and I understand it.', ackb: 'Record my acknowledgement', acked: 'Acknowledgement recorded', ref: 'reference', none: 'No offer was made on this case, so there is no statement.',
    back: 'Back', print: 'Print', note: 'This statement is available in English and Hindi (use the language toggle). The Hindi text has not been reviewed by a legal translator; a lender must have it reviewed before use. The Directions require the statement in a language the borrower understands.', spread: 'spread', reset: 'reset', rp: 'Risk premium',
    lender: 'Lender to state', c: ['Month', 'Opening balance', 'Principal', 'Interest', 'Instalment'], impact: 'Change for a 25 bps change in the final rate', emi: 'Instalment', epi: 'Number of instalments' },
  hi: { title: 'मुख्य तथ्य विवरण (KFS)', sub: 'प्रारूप: RBI (NBFC - उत्तरदायी व्यवसाय आचरण) निर्देश, 2025, अनुलग्नक I', p1: 'भाग 1: ब्याज दर, शुल्क और प्रभार', p2: 'भाग 2: अन्य गुणात्मक जानकारी',
    apr: 'वार्षिक प्रतिशत दर (APR) की गणना', sch: 'चुकौती अनुसूची', prop: 'प्रस्ताव संख्या', valid: 'स्वीकार करने की अंतिम तिथि', validb: 'कम से कम तीन कार्य दिवस। इस अवधि में आप स्वीकार करें तो ऋणदाता इन शर्तों से बँधा है।',
    ack: 'मैंने यह विवरण पढ़ा है, इसकी सामग्री मुझे समझाई गई है, और मैं इसे समझता/समझती हूँ।', ackb: 'मेरी स्वीकृति दर्ज करें', acked: 'स्वीकृति दर्ज हुई', ref: 'संदर्भ', none: 'इस मामले में कोई प्रस्ताव नहीं है, इसलिए कोई विवरण नहीं।',
    back: 'वापस', print: 'प्रिंट', note: 'यह विवरण हिंदी और अंग्रेज़ी में उपलब्ध है (भाषा बटन से बदलें)। हिंदी पाठ की किसी विधिक अनुवादक ने समीक्षा नहीं की है; उपयोग से पहले ऋणदाता को समीक्षा करानी होगी। निर्देशों के अनुसार विवरण उधारकर्ता की समझ की भाषा में होना चाहिए।', spread: 'स्प्रेड', reset: 'पुनर्निर्धारण', rp: 'जोखिम प्रीमियम',
    lender: 'ऋणदाता बताएगा', c: ['माह', 'आरंभिक शेष', 'मूलधन', 'ब्याज', 'किस्त'], impact: 'अंतिम दर में 25 आधार अंकों के बदलाव का असर', emi: 'किस्त', epi: 'किस्तों की संख्या' },
}

function Tbl({ items, val }: { items: J[]; val: (v: J) => ReactNode }) {
  return (
    <table className="chart w-full"><tbody>{items.map(i => <tr key={i.no}><th scope="row" className="w-10 align-top">{i.no}</th><td className="align-top w-[36%] font-medium">{i.item}</td><td className={i.lender_to_set ? 'italic' : ''}>{val(i.value)}</td></tr>)}</tbody></table>
  )
}

export default function Kfs() {
  const { id } = useParams()
  const { t, lang } = useI18n()
  const x = T[lang] ?? T.en
  const [c, setC] = useState<J | null>(null)
  const [rows, setRows] = useState<J[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const load = () => api('/cases/' + id).then(setC).catch(e => setErr(e.message))
  useEffect(() => {
    if (!id) return
    adoptKeyFromHash(id); load()
    api(`/cases/${id}/schedule`).then(r => setRows(r.rows)).catch(() => setRows([]))
  }, [id])
  if (err) return <div className="p-6"><Notice tone="bad">{err}</Notice></div>
  if (!c) return <div className="p-6"><Spinner label={t('common.loading')} /></div>
  const k = c.decision?.kfs
  if (c.erased || !k) return <div className="p-6"><Notice>{x.none}</Notice><p><Link to={`/case/${id}`} className="underline text-blue font-display font-bold">{x.back}</Link></p></div>
  const loc = lang === 'hi' && k.hi ? k.hi : k
  const a = loc.annex_i
  const val = (v: J): ReactNode => {
    if (typeof v === 'string') return v
    if (v.reference_benchmark) return <>{v.reference_benchmark} {v.benchmark_pct}% + {x.spread} {v.spread_pct}% = {v.final_rate_pct}%. {x.reset}: {v.reset_periodicity}. {x.impact}: {x.emi} {v.impact_of_25_bps.emi_change >= 0 ? '+' : ''}{inr(v.impact_of_25_bps.emi_change)}, {x.epi} +{v.impact_of_25_bps.epi_count_change}</>
    if (v.payable_to_lender) return <>{v.payable_to_lender.map((f: J) => `${f.name}: ${f.type}, ${f.amount}`).join('; ')}. {v.payable_to_third_party_via_lender.map((f: J) => `${f.name}: ${f.amount}`).join('; ')}</>
    return <ul className="m-0 pl-4">{Object.entries(v).map(([kk, vv]) => <li key={kk}>{kk.replace(/_/g, ' ')}: {String(vv)}</li>)}</ul>
  }
  async function ack() { setBusy(true); try { await api(`/cases/${id}/kfs-ack`, {}); await load() } catch (e) { setErr((e as Error).message) } setBusy(false) }
  return (
    <div className="mx-auto max-w-[900px] px-5 py-6">
      <div className="no-print flex items-center justify-between gap-3 mb-5">
        <Link to={`/case/${c.case_id}`} className="inline-flex items-center gap-2 font-display font-semibold underline text-blue"><ArrowLeft size={18} weight="bold" aria-hidden />{x.back}</Link>
        <Btn onClick={() => window.print()}><Printer size={18} weight="bold" aria-hidden />{x.print}</Btn>
      </div>
      <article className="letter sheet p-8 sm:p-10" lang={lang}>
        <header className="pb-4 border-b-2 border-rule flex items-start justify-between gap-6">
          <div><h1 className="m-0 text-2xl font-bold">{x.title}</h1><p className="m-0 mt-1 text-sm text-ink2">{x.sub}</p></div>
          <div className="text-right text-sm"><div className="mono">{x.prop}: {k.proposal_no}</div><div>{x.valid}: <b>{c.kfs_valid_until}</b></div></div>
        </header>
        <p className="mt-3 text-sm">{x.validb}</p>
        <h2 className="mt-5 text-lg font-bold">{x.p1}</h2><Tbl val={val} items={a.part1.map((i: J) => i.no === 1 ? { ...i, value: `${k.proposal_no} · ${i.value}` } : i)} />
        <h2 className="mt-6 text-lg font-bold">{x.p2}</h2><Tbl val={val} items={a.part2} />
        <h2 className="mt-6 text-lg font-bold">{x.apr}</h2>
        <table className="chart w-full"><tbody>{a.apr_sheet.map((r: string[], i: number) => <tr key={i}><td>{i + 1}. {r[0]}</td><td className="r num">{r[1]}</td></tr>)}</tbody></table>
        <h2 className="mt-6 text-lg font-bold">{x.sch}</h2>
        <table className="chart w-full"><thead><tr>{x.c.map((h, i) => <th key={i} className={i ? 'r' : ''}>{h}</th>)}</tr></thead>
          <tbody>{rows.map(r => <tr key={r.n}><td>{r.n}</td><td className="r num">{inr(r.outstanding)}</td><td className="r num">{inr(r.principal)}</td><td className="r num">{inr(r.interest)}</td><td className="r num">{inr(r.emi)}</td></tr>)}</tbody></table>
        <ul className="mt-6 pl-5 grid gap-1 text-sm">{loc.other_disclosures.map((d: J) => <li key={d.id}><b>{d.label}.</b> {d.value} <span className="text-ink2">({d.basis})</span></li>)}</ul>
        <div className="no-print mt-8 border-t-2 border-faint pt-5 grid gap-3">
          <p className="m-0 font-medium">{x.ack}</p>
          {c.kfs_ack ? <Notice tone="ok" title={x.acked}>{x.ref} <span className="mono">{c.kfs_ack.reference}</span> · {c.kfs_ack.at}</Notice> : <div><Btn disabled={busy} onClick={ack}>{x.ackb}</Btn></div>}
          <Notice>{x.note}</Notice>
        </div>
      </article>
    </div>
  )
}
