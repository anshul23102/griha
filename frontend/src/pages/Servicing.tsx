import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from '@phosphor-icons/react'
import { api, adoptKeyFromHash, session, inr, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Notice, Sheet, Spinner } from '../components/kit'

// What follows a sanction, built from the primary text of RBI Responsible Business Conduct Directions 2025 (paras 31(6), 35 to 41, 93 to 101) and the HFC Directions
// 2025 (para 170): the quarterly statement, release of property documents with the daily compensation, and the rules for recovery agents.
const T = {
  en: {
    hi: 'सेवा एवं आचरण', title: 'Loan servicing and conduct', lead: 'The duties that follow a sanction, enforced as rules. No loan is disbursed in this prototype, so the statement is illustrative.', back: 'Back to the case',
    qs: 'Quarterly statement', qsSub: 'RBC Directions 2025 para 31(6): principal and interest recovered, EMI, EMIs left and APR, at the end of every quarter.', months: 'Months after disbursal (illustration)',
    cols: ['Quarter', 'Period end', 'Principal recovered', 'Interest recovered', 'EMI', 'EMIs left', 'APR'], none: 'No quarter has completed yet.',
    cl: 'Closing the loan and releasing the documents', clSub: 'RBC Directions 2025 paras 35 to 41. Original documents and charge removal within 30 days of full repayment; Rs 5,000 a day for a delay that is the lender\'s; 60 days where documents are lost or damaged.',
    repaid: 'Date of full repayment', released: 'Date the documents were released (leave empty if not yet)', place: 'Where the borrower collects them', damaged: 'Documents were lost or damaged', reason: 'Reason given to the borrower for any delay (para 39)', record: 'Record',
    dueBy: 'Release due by', status: 'Status', late: 'Days late', comp: 'Compensation due', open: 'No full repayment has been recorded.', st: { 'within time': 'Within time', overdue: 'Overdue', released: 'Released', open: 'Open' } as Record<string, string>,
    ra: 'Recovery agencies and conduct', raSub: 'RBC Directions 2025 paras 93 to 101 and HFC Directions 2025 para 170. The list of agencies is public (para 97). Staff can check a contact before it is made.',
    agName: 'Agency', period: 'Empanelled', phone: 'Phone', current: 'Current', noAg: 'No agency is empanelled yet.',
    chk: 'Check a recovery contact', agent: 'Agency name', at: 'Date and time (India time)', ch: 'Channel', target: 'Who is contacted', rec: 'The borrower was told the call is recorded', occ: 'Bereavement, wedding or festival', summary: 'What it was about', run: 'Check and record',
    ok: 'Allowed and recorded.', refused: 'Refused and logged:', staffOnly: 'Staff can record repayments and check recovery contacts. Sign in on the Lender desk.',
  },
  hi: {
    hi: 'Loan servicing and conduct', title: 'ऋण सेवा एवं आचरण', lead: 'स्वीकृति के बाद के दायित्व, नियमों के रूप में लागू। इस प्रोटोटाइप में कोई ऋण वितरित नहीं होता, इसलिए विवरण उदाहरण है।', back: 'मामले पर वापस',
    qs: 'त्रैमासिक विवरण', qsSub: 'RBC निर्देश 2025 पैरा 31(6): हर तिमाही के अंत में वसूला मूलधन और ब्याज, किस्त, शेष किस्तें और APR।', months: 'वितरण के बाद माह (उदाहरण)',
    cols: ['तिमाही', 'अवधि समाप्ति', 'वसूला मूलधन', 'वसूला ब्याज', 'किस्त', 'शेष किस्तें', 'APR'], none: 'अभी कोई तिमाही पूरी नहीं हुई।',
    cl: 'ऋण बंद करना और दस्तावेज़ लौटाना', clSub: 'RBC निर्देश 2025 पैरा 35 से 41। पूर्ण चुकौती के 30 दिनों के भीतर मूल दस्तावेज़ और प्रभार हटाना; ऋणदाता की देरी पर ₹5,000 प्रतिदिन; दस्तावेज़ खोने या खराब होने पर 60 दिन।',
    repaid: 'पूर्ण चुकौती की तिथि', released: 'दस्तावेज़ लौटाने की तिथि (अभी नहीं तो खाली छोड़ें)', place: 'उधारकर्ता कहाँ से लेगा', damaged: 'दस्तावेज़ खो गए या खराब हुए', reason: 'देरी का कारण जो उधारकर्ता को बताया (पैरा 39)', record: 'दर्ज करें',
    dueBy: 'लौटाने की अंतिम तिथि', status: 'स्थिति', late: 'देरी के दिन', comp: 'देय मुआवज़ा', open: 'पूर्ण चुकौती दर्ज नहीं हुई है।', st: { 'within time': 'समय के भीतर', overdue: 'विलंबित', released: 'लौटाए गए', open: 'खुला' } as Record<string, string>,
    ra: 'वसूली एजेंसियाँ और आचरण', raSub: 'RBC निर्देश 2025 पैरा 93 से 101 और HFC निर्देश 2025 पैरा 170। एजेंसियों की सूची सार्वजनिक है (पैरा 97)। कर्मचारी संपर्क से पहले उसे जाँच सकते हैं।',
    agName: 'एजेंसी', period: 'पैनल अवधि', phone: 'फ़ोन', current: 'वर्तमान', noAg: 'अभी कोई एजेंसी पैनल में नहीं है।',
    chk: 'वसूली संपर्क जाँचें', agent: 'एजेंसी का नाम', at: 'तारीख और समय (भारतीय समय)', ch: 'माध्यम', target: 'किससे संपर्क', rec: 'उधारकर्ता को बताया गया कि कॉल रिकॉर्ड हो रही है', occ: 'शोक, विवाह या त्योहार', summary: 'किस बारे में', run: 'जाँचें और दर्ज करें',
    ok: 'अनुमत और दर्ज।', refused: 'अस्वीकृत और लॉग:', staffOnly: 'कर्मचारी चुकौती दर्ज कर सकते हैं और वसूली संपर्क जाँच सकते हैं। ऋणदाता डेस्क पर साइन इन करें।',
  },
}
const field = 'min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none w-full'
const Lbl = ({ l, children }: { l: string; children: ReactNode }) => <label className="grid gap-1 font-medium">{l}{children}</label>

export default function Servicing() {
  const { id } = useParams()
  const { lang } = useI18n()
  const x = T[lang] ?? T.en
  const staff = !!session()
  const [qs, setQs] = useState<J | null>(null)
  const [months, setMonths] = useState(12)
  const [cl, setCl] = useState<J | null>(null)
  const [agents, setAgents] = useState<J[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [f, setF] = useState({ repaid_on: '', released_on: '', collection_place: 'the branch or office that serviced the account', damaged: false, delay_reason: '' })
  const [k, setK] = useState({ agent: '', at: '', channel: 'call', target: 'borrower', recorded_notice_given: true, sensitive_occasion: false, summary: '' })
  const [res, setRes] = useState<J | null>(null)
  useEffect(() => { if (id) { adoptKeyFromHash(id); api(`/cases/${id}/closure`).then(setCl).catch(() => {}) } }, [id])
  useEffect(() => { if (id) api(`/cases/${id}/statements?months=${months}`).then(setQs).catch(e => setErr(e.message)) }, [id, months])
  useEffect(() => { api('/recovery-agents').then(setAgents).catch(() => {}) }, [])
  const run = async (fn: () => Promise<void>) => { setErr(null); try { await fn() } catch (e) { setErr((e as Error).message) } }
  const body = Object.fromEntries(Object.entries({ ...f, released_on: f.released_on || null, delay_reason: f.delay_reason || null }))
  if (!qs && !err) return <div className="p-6"><Spinner label="…" /></div>
  return (
    <div className="flex flex-col gap-6">
      <Board hi={x.hi} en={lang === 'hi' ? x.title : x.title} aside={<Link to={`/case/${id}`} className="inline-flex items-center gap-2 underline font-display font-semibold"><ArrowLeft size={16} weight="bold" aria-hidden />{x.back}</Link>}>
        <p className="m-0 mt-2 font-medium max-w-[64ch]">{x.lead}</p>
      </Board>
      {err && <Notice tone="bad">{err}</Notice>}

      <Sheet title={x.qs} sub={x.qsSub}>
        <div className="px-5 py-4 flex items-end gap-4 flex-wrap">
          <Lbl l={x.months}><input type="number" min={3} max={600} step={3} value={months} onChange={e => setMonths(Number(e.target.value))} className={field + ' w-40'} /></Lbl>
          <p className="m-0 text-sm text-ink2 max-w-[60ch]">{qs?.note}</p>
        </div>
        {qs && qs.statements.length > 0 ? <div className="overflow-x-auto"><table className="chart min-w-[720px]"><thead><tr>{x.cols.map((c: string, i: number) => <th key={c} className={i > 1 ? 'r' : ''}>{c}</th>)}</tr></thead>
          <tbody>{qs.statements.map((s: J) => <tr key={s.quarter}><td className="num">{s.quarter}</td><td className="num">{s.period_end}</td><td className="r num">{inr(s.principal_recovered)}</td><td className="r num">{inr(s.interest_recovered)}</td><td className="r num">{inr(s.emi)}</td><td className="r num">{s.emis_left}</td><td className="r num">{s.apr_pct}%</td></tr>)}</tbody></table></div>
          : <p className="m-0 px-5 pb-4 text-ink2">{x.none}</p>}
      </Sheet>

      <Sheet title={x.cl} sub={x.clSub}>
        <div className="px-5 py-4 grid gap-3">
          {cl && cl.status !== 'open' ? (
            <table className="chart"><tbody>
              <tr><th scope="row">{x.status}</th><td className={`font-bold ${cl.status === 'overdue' ? 'text-bad' : cl.status === 'released' ? 'text-ok' : ''}`}>{x.st[cl.status] ?? cl.status}</td></tr>
              <tr><th scope="row">{x.dueBy}</th><td className="num">{cl.release_due_by}</td></tr>
              <tr><th scope="row">{x.late}</th><td className="num">{cl.days_late}</td></tr>
              <tr><th scope="row">{x.comp}</th><td className="num font-bold">{inr(cl.compensation_inr)}</td></tr>
            </tbody></table>) : <p className="m-0 text-ink2">{x.open}</p>}
          {cl?.must_do && <ul className="m-0 pl-5 text-sm text-ink2 grid gap-1">{cl.must_do.map((m: string) => <li key={m}>{m}</li>)}</ul>}
          {staff ? (
            <div className="grid gap-3 sm:grid-cols-2 max-w-[820px] mt-2">
              <Lbl l={x.repaid}><input type="date" className={field} value={f.repaid_on} onChange={e => setF({ ...f, repaid_on: e.target.value })} /></Lbl>
              <Lbl l={x.released}><input type="date" className={field} value={f.released_on} onChange={e => setF({ ...f, released_on: e.target.value })} /></Lbl>
              <Lbl l={x.place}><input className={field} value={f.collection_place} onChange={e => setF({ ...f, collection_place: e.target.value })} /></Lbl>
              <Lbl l={x.reason}><input className={field} value={f.delay_reason} onChange={e => setF({ ...f, delay_reason: e.target.value })} /></Lbl>
              <label className="flex items-center gap-2 font-medium"><input type="checkbox" checked={f.damaged} onChange={e => setF({ ...f, damaged: e.target.checked })} />{x.damaged}</label>
              <div><Btn disabled={!f.repaid_on} onClick={() => run(async () => setCl(await api(`/cases/${id}/closure`, body)))}>{x.record}</Btn></div>
            </div>) : <Notice>{x.staffOnly}</Notice>}
        </div>
      </Sheet>

      <Sheet title={x.ra} sub={x.raSub}>
        {agents.length ? <div className="overflow-x-auto"><table className="chart min-w-[560px]"><thead><tr><th>{x.agName}</th><th>{x.period}</th><th>{x.phone}</th><th>{x.current}</th></tr></thead>
          <tbody>{agents.map(a => <tr key={a.name}><td className="font-medium">{a.name}</td><td className="num">{a.empanelled_from} to {a.empanelled_to}</td><td className="num">{a.phone}</td><td className={a.current ? 'text-ok font-bold' : 'text-bad'}>{a.current ? '✓' : '✗'}</td></tr>)}</tbody></table></div>
          : <p className="m-0 px-5 py-4 text-ink2">{x.noAg}</p>}
        {staff && (
          <div className="px-5 py-4 grid gap-3 sm:grid-cols-2 max-w-[820px] border-t border-faint">
            <h3 className="m-0 sm:col-span-2 text-base font-bold">{x.chk}</h3>
            <Lbl l={x.agent}><input className={field} value={k.agent} onChange={e => setK({ ...k, agent: e.target.value })} list="agents" /></Lbl>
            <datalist id="agents">{agents.map(a => <option key={a.name} value={a.name} />)}</datalist>
            <Lbl l={x.at}><input type="datetime-local" className={field} value={k.at} onChange={e => setK({ ...k, at: e.target.value })} /></Lbl>
            <Lbl l={x.ch}><select className={field} value={k.channel} onChange={e => setK({ ...k, channel: e.target.value })}>{['call', 'visit', 'sms', 'letter'].map(v => <option key={v}>{v}</option>)}</select></Lbl>
            <Lbl l={x.target}><select className={field} value={k.target} onChange={e => setK({ ...k, target: e.target.value })}>{['borrower', 'guarantor', 'relative', 'referee', 'friend', 'employer'].map(v => <option key={v}>{v}</option>)}</select></Lbl>
            <label className="flex items-center gap-2 font-medium"><input type="checkbox" checked={k.recorded_notice_given} onChange={e => setK({ ...k, recorded_notice_given: e.target.checked })} />{x.rec}</label>
            <label className="flex items-center gap-2 font-medium"><input type="checkbox" checked={k.sensitive_occasion} onChange={e => setK({ ...k, sensitive_occasion: e.target.checked })} />{x.occ}</label>
            <div className="sm:col-span-2"><Lbl l={x.summary}><input className={field} value={k.summary} onChange={e => setK({ ...k, summary: e.target.value })} /></Lbl></div>
            <div><Btn disabled={!k.agent || !k.at || k.summary.length < 3} onClick={() => run(async () => setRes(await api(`/cases/${id}/recovery-contact`, { ...k, at: new Date(k.at + ':00+05:30').toISOString() })))}>{x.run}</Btn></div>
            {res && <div className="sm:col-span-2"><Notice tone={res.allowed ? 'ok' : 'bad'} title={res.allowed ? x.ok : x.refused}>{res.allowed ? `#${res.reference}` : <ul className="m-0 pl-5">{res.violations.map((v: J) => <li key={v.rule}>{v.text} <span className="text-ink2">({v.cite})</span></li>)}</ul>}</Notice></div>}
          </div>)}
      </Sheet>
    </div>
  )
}
