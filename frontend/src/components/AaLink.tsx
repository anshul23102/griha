import { useState } from 'react'
import { api, type J } from '../api'
import { useI18n } from '../i18n'
import { Btn, Notice, Spinner } from './kit'

// Linking a bank account through the Account Aggregator protocol: signed consent request, approval in the Aggregator's app, signed artefact, encrypted data, decryption.
// The Aggregator here is a mock that runs in our own server (the page says so). The FIU side is real protocol code, tested against it.
const T = {
  en: { h: 'Or link your bank through the Account Aggregator protocol', sub: 'A sandbox: our server acts as the Financial Information User and talks to a mock Aggregator, using signed requests and encrypted data as the ReBIT/Sahamati documents describe.',
    start: 'Request consent', need: 'Fill your name and mobile number in step 1 first.', consentTitle: 'Consent request from Griha (the Financial Information User)', purpose: 'Purpose', data: 'Data', range: 'Period', until: 'Valid until',
    once: 'One time only', approve: 'Approve in the Aggregator app', reject: 'Reject', fetch: 'Fetch my bank data', rejected: 'You rejected the consent. Nothing was shared.', done: 'Bank data received, decrypted and read:', trace: 'What happened, step by step', mock: 'Mock Aggregator, not a real one' },
  hi: { h: 'या अपना बैंक अकाउंट एग्रीगेटर प्रोटोकॉल से जोड़ें', sub: 'सैंडबॉक्स: हमारा सर्वर वित्तीय सूचना उपयोगकर्ता (FIU) बनकर एक नकली एग्रीगेटर से बात करता है, ReBIT/Sahamati दस्तावेज़ों के अनुसार हस्ताक्षरित अनुरोध और एन्क्रिप्टेड डेटा के साथ।',
    start: 'सहमति का अनुरोध करें', need: 'पहले चरण 1 में अपना नाम और मोबाइल नंबर भरें।', consentTitle: 'Griha (वित्तीय सूचना उपयोगकर्ता) की सहमति का अनुरोध', purpose: 'उद्देश्य', data: 'डेटा', range: 'अवधि', until: 'वैधता',
    once: 'केवल एक बार', approve: 'एग्रीगेटर ऐप में स्वीकृत करें', reject: 'अस्वीकार करें', fetch: 'मेरा बैंक डेटा लाएँ', rejected: 'आपने सहमति अस्वीकार की। कुछ साझा नहीं हुआ।', done: 'बैंक डेटा मिला, डिक्रिप्ट हुआ और पढ़ा गया:', trace: 'चरण दर चरण क्या हुआ', mock: 'नकली एग्रीगेटर, असली नहीं' },
}

export default function AaLink({ name, phone, onDoc }: { name: string; phone: string; onDoc: (d: J) => void }) {
  const { lang } = useI18n()
  const x = T[lang] ?? T.en
  const [c, setC] = useState<J | null>(null)
  const [state, setState] = useState<'idle' | 'pending' | 'active' | 'rejected' | 'done'>('idle')
  const [trace, setTrace] = useState<J[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const ready = name.trim().length >= 2 && /^[6-9][0-9]{9}$/.test(phone.replace(/\D/g, '').slice(-10))
  const go = async (fn: () => Promise<void>) => { setErr(null); setBusy(true); try { await fn() } catch (e) { setErr((e as Error).message) } setBusy(false) }
  return (
    <div className="border-2 border-faint p-4 grid gap-3" data-testid="aa-link">
      <h3 className="m-0 text-base font-bold">{x.h}</h3>
      <p className="m-0 text-sm text-ink2">{x.sub}</p>
      {state === 'idle' && (<><Btn kind="ghost" disabled={!ready || busy} onClick={() => go(async () => { const r = await api('/aa/consent', { phone: phone.replace(/\D/g, '').slice(-10), name }); setC(r); setTrace(r.trace); setState('pending') })}>{x.start}</Btn>
        {!ready && <p className="m-0 text-sm text-ink2">{x.need}</p>}</>)}
      {state !== 'idle' && c && (
        <div className="grid gap-2 border-2 border-rule p-4">
          <div className="mono text-xs text-ink2">{x.mock}: {c.aggregator}</div>
          <h4 className="m-0 text-base font-bold">{x.consentTitle}</h4>
          <table className="chart"><tbody>
            <tr><th scope="row" className="font-normal">{x.purpose}</th><td>{c.consent.purpose}</td></tr>
            <tr><th scope="row" className="font-normal">{x.data}</th><td className="mono">{c.consent.fi_types.join(', ')}: {c.consent.data.join(', ')}</td></tr>
            <tr><th scope="row" className="font-normal">{x.range}</th><td className="num">{c.consent.from} → {c.consent.to}</td></tr>
            <tr><th scope="row" className="font-normal">{x.until}</th><td className="num">{c.consent.valid_until} · {x.once}</td></tr>
          </tbody></table>
          {state === 'pending' && <div className="flex gap-3 flex-wrap">
            <Btn disabled={busy} onClick={() => go(async () => { await api(`/aa/consent/${c.handle}/decide`, { approve: true }); setState('active') })}>{x.approve}</Btn>
            <Btn kind="ghost" disabled={busy} onClick={() => go(async () => { await api(`/aa/consent/${c.handle}/decide`, { approve: false }); setState('rejected') })}>{x.reject}</Btn></div>}
          {state === 'active' && <div><Btn disabled={busy} onClick={() => go(async () => { const d = await api(`/aa/fetch/${c.handle}`, {}); setTrace(d.trace); onDoc(d); setState('done') })}>{x.fetch}</Btn></div>}
          {state === 'rejected' && <Notice tone="warn">{x.rejected}</Notice>}
          {state === 'done' && <Notice tone="ok">{x.done} {trace.length} steps.</Notice>}
          {trace.length > 0 && <details open={state === 'done'}><summary className="cursor-pointer font-medium">{x.trace}</summary>
            <ol className="m-0 mt-2 pl-5 text-sm grid gap-1">{trace.map((t, i) => <li key={i}><span className="mono">{t.step}</span> <span className="text-ink2">{t.detail}</span></li>)}</ol></details>}
        </div>)}
      {busy && <Spinner label="…" />}
      {err && <Notice tone="bad">{err}</Notice>}
    </div>
  )
}
