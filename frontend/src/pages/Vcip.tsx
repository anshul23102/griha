import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Camera, MapPin } from '@phosphor-icons/react'
import { api, adoptKeyFromHash, session, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Notice, Sheet } from '../components/kit'

// Video-based Customer Identification Process (V-CIP): the procedure of NBFC KYC Directions 2025 paras 26 and 27 as a checklist the system enforces.
// What it does not do: record or store live video. The demo also puts the customer and the official in one browser, which a real V-CIP never does.
const T = {
  en: { hi: 'वीडियो केवाईसी', title: 'Video KYC (V-CIP)', lead: 'A trained official runs the session. Every mandatory element must be on record, each with the paragraph that requires it, or the session cannot be completed.', back: 'Back to the case',
    start: 'Start a session', startNote: 'Each session gets its own random questions (para 27(2)(iii)). After a dropped call, start a new session.', q: 'Questions for this session', pass: 'Asked, passed', fail: 'Asked, failed',
    geo: 'Capture the customer\'s live location', photo: 'Capture the customer\'s photograph', panImg: 'Capture the PAN card image', epan: 'The customer gave an e-PAN instead', route: 'How the identification information was obtained', obtained: 'Date it was obtained (at most 3 working days ago)',
    profile: 'The customer confirmed their economic and financial profile', addr: 'The current address differs from the document', addrRec: 'The current address was recorded', live: 'The liveness check passed', prompt: 'Prompting was observed at the customer\'s end', dropped: 'The call dropped',
    submit: 'Complete the session', passed: 'Session passed. Identity confirmed by V-CIP.', failed: 'Session cannot be completed:', reject: 'The process must be REJECTED (para 27(2)(iv)).', captured: 'captured', hashNote: 'Only a SHA-256 hash of each image is kept here. The image itself would go to the lender\'s encrypted store.',
    mock: 'Demo: customer and official share this browser. A real V-CIP never does.' },
  hi: { hi: 'Video KYC (V-CIP)', title: 'वीडियो केवाईसी (V-CIP)', lead: 'प्रशिक्षित अधिकारी सत्र चलाता है। हर अनिवार्य तत्व दर्ज होना चाहिए, साथ में उसे माँगने वाला पैरा, वरना सत्र पूरा नहीं हो सकता।', back: 'मामले पर वापस',
    start: 'सत्र शुरू करें', startNote: 'हर सत्र के अपने यादृच्छिक प्रश्न होते हैं (पैरा 27(2)(iii))। कॉल कटने पर नया सत्र शुरू करें।', q: 'इस सत्र के प्रश्न', pass: 'पूछा, सफल', fail: 'पूछा, असफल',
    geo: 'ग्राहक का लाइव स्थान लें', photo: 'ग्राहक की फोटो लें', panImg: 'PAN कार्ड की छवि लें', epan: 'ग्राहक ने e-PAN दिया', route: 'पहचान जानकारी कैसे प्राप्त हुई', obtained: 'प्राप्ति की तिथि (अधिकतम 3 कार्य दिवस पुरानी)',
    profile: 'ग्राहक ने अपनी आर्थिक और वित्तीय प्रोफ़ाइल की पुष्टि की', addr: 'वर्तमान पता दस्तावेज़ से अलग है', addrRec: 'वर्तमान पता दर्ज किया गया', live: 'लाइवनेस जाँच सफल रही', prompt: 'ग्राहक की ओर से प्रॉम्प्टिंग देखी गई', dropped: 'कॉल कट गई',
    submit: 'सत्र पूरा करें', passed: 'सत्र सफल। V-CIP से पहचान की पुष्टि हुई।', failed: 'सत्र पूरा नहीं हो सकता:', reject: 'प्रक्रिया अस्वीकृत की जानी चाहिए (पैरा 27(2)(iv))।', captured: 'ली गई', hashNote: 'यहाँ हर छवि का केवल SHA-256 हैश रखा जाता है। छवि ऋणदाता के एन्क्रिप्टेड भंडार में जाएगी।',
    mock: 'डेमो: ग्राहक और अधिकारी एक ही ब्राउज़र में हैं। असली V-CIP में ऐसा कभी नहीं होता।' },
}
const field = 'min-h-11 px-3 bg-sheet text-ink border-2 border-rule rounded-none w-full'
const sha256 = async (b: ArrayBuffer) => [...new Uint8Array(await crypto.subtle.digest('SHA-256', b))].map(x => x.toString(16).padStart(2, '0')).join('')

export default function Vcip() {
  const { id } = useParams()
  const { lang } = useI18n()
  const x = T[lang] ?? T.en
  const [sess, setSess] = useState<J | null>(null)
  const [d, setD] = useState({ identification_method: 'aadhaar_otp', id_obtained_on: new Date().toISOString().slice(0, 10), financial_profile_confirmed: false, address_differs: false, current_address_recorded: false,
    liveness_passed: false, prompting_observed: false, epan: false, dropped: false })
  const [geo, setGeo] = useState<J | null>(null)
  const [photo, setPhoto] = useState<string | null>(null)
  const [pan, setPan] = useState<string | null>(null)
  const [answers, setAnswers] = useState<Record<string, boolean>>({})
  const [res, setRes] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const video = useRef<HTMLVideoElement>(null)
  if (id) adoptKeyFromHash(id)
  const run = async (fn: () => Promise<void>) => { setErr(null); try { await fn() } catch (e) { setErr((e as Error).message) } }
  const where = () => run(async () => { const p = await new Promise<GeolocationPosition>((ok, no) => navigator.geolocation.getCurrentPosition(ok, no, { enableHighAccuracy: true, timeout: 15000 })); setGeo({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy }) })
  const snap = (set: (h: string) => void) => run(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    const v = video.current!; v.srcObject = stream; await v.play(); await new Promise(r => setTimeout(r, 600))
    const c = document.createElement('canvas'); c.width = v.videoWidth || 320; c.height = v.videoHeight || 240; c.getContext('2d')!.drawImage(v, 0, 0)
    stream.getTracks().forEach(t => t.stop()); v.srcObject = null
    const blob = await new Promise<Blob>(r => c.toBlob(b => r(b!), 'image/jpeg', 0.8)); set(await sha256(await blob.arrayBuffer()))
  })
  if (!session()) return <div className="p-6"><Notice>Sign in on the Lender desk to run a V-CIP session.</Notice></div>
  return (
    <div className="flex flex-col gap-6">
      <Board hi={x.hi} en={x.title} aside={<Link to={`/case/${id}`} className="inline-flex items-center gap-2 underline font-display font-semibold"><ArrowLeft size={16} weight="bold" aria-hidden />{x.back}</Link>}><p className="m-0 mt-2 font-medium max-w-[64ch]">{x.lead}</p></Board>
      {err && <Notice tone="bad">{err}</Notice>}
      <Notice tone="info">{x.mock}</Notice>
      {!sess && <Sheet title={x.start} sub={x.startNote}><div className="px-5 py-4"><Btn onClick={() => run(async () => { setSess(await api(`/cases/${id}/vcip/start`, {})); setRes(null) })}>{x.start}</Btn></div></Sheet>}
      {sess && (
        <>
          <Sheet title={x.q}>
            <ol className="m-0 px-5 py-4 pl-10 grid gap-3">{sess.questions.map((q: J) => (
              <li key={q.id}><span className="mono text-xs text-ink2">{q.id} · {q.kind}</span><div className="font-medium">{q.text}</div>
                <div className="flex gap-4 mt-1 text-sm"><label className="flex items-center gap-1"><input type="radio" name={q.id} checked={answers[q.id] === true} onChange={() => setAnswers({ ...answers, [q.id]: true })} />{x.pass}</label>
                  <label className="flex items-center gap-1"><input type="radio" name={q.id} checked={answers[q.id] === false} onChange={() => setAnswers({ ...answers, [q.id]: false })} />{x.fail}</label></div></li>))}</ol>
          </Sheet>
          <Sheet title="Record" sub={x.hashNote}>
            <div className="px-5 py-4 grid gap-4 sm:grid-cols-2 max-w-[900px]">
              <video ref={video} className="hidden" playsInline muted />
              <div className="grid gap-2"><Btn kind="ghost" onClick={where}><MapPin size={18} weight="bold" aria-hidden />{x.geo}</Btn>{geo && <span className="mono text-sm">{geo.lat.toFixed(4)}, {geo.lon.toFixed(4)} · ±{Math.round(geo.accuracy)} m · {x.captured}</span>}</div>
              <div className="grid gap-2"><Btn kind="ghost" onClick={() => snap(setPhoto)}><Camera size={18} weight="bold" aria-hidden />{x.photo}</Btn>{photo && <span className="mono text-sm">sha256 {photo.slice(0, 16)}… {x.captured}</span>}</div>
              <div className="grid gap-2"><Btn kind="ghost" disabled={d.epan} onClick={() => snap(setPan)}><Camera size={18} weight="bold" aria-hidden />{x.panImg}</Btn>{pan && <span className="mono text-sm">sha256 {pan.slice(0, 16)}… {x.captured}</span>}</div>
              <label className="flex items-center gap-2 font-medium"><input type="checkbox" checked={d.epan} onChange={e => setD({ ...d, epan: e.target.checked })} />{x.epan}</label>
              <label className="grid gap-1 font-medium">{x.route}<select className={field} value={d.identification_method} onChange={e => setD({ ...d, identification_method: e.target.value })}>
                {Object.entries(sess.routes).map(([k, v]) => <option key={k} value={k}>{String(v)}</option>)}</select></label>
              <label className="grid gap-1 font-medium">{x.obtained}<input type="date" className={field} value={d.id_obtained_on} onChange={e => setD({ ...d, id_obtained_on: e.target.value })} /></label>
              {([['financial_profile_confirmed', x.profile], ['address_differs', x.addr], ['current_address_recorded', x.addrRec], ['liveness_passed', x.live], ['prompting_observed', x.prompt], ['dropped', x.dropped]] as [keyof typeof d, string][]).map(([k, l]) => (
                <label key={k} className="flex items-center gap-2 font-medium"><input type="checkbox" checked={!!d[k]} onChange={e => setD({ ...d, [k]: e.target.checked })} />{l}</label>))}
              <div className="sm:col-span-2"><Btn onClick={() => run(async () => {
                const { dropped, ...rest } = d
                setRes(await api(`/cases/${id}/vcip/${sess.session_id}/complete`, { ...rest, disruption: dropped ? 'dropped' : 'none', geo: geo ?? {}, photo_sha256: photo, pan_image_sha256: pan, answers: Object.entries(answers).map(([qid, ok]) => ({ id: qid, ok })) }))
              })}>{x.submit}</Btn></div>
              {res && <div className="sm:col-span-2"><Notice tone={res.passed ? 'ok' : 'bad'} title={res.passed ? x.passed : x.failed}>{res.passed ? '' : <ul className="m-0 pl-5">{res.reasons.map((r: J) => <li key={r.rule}>{r.text} <span className="text-ink2">({r.cite})</span></li>)}</ul>}{res.must_reject && <b>{x.reject}</b>}</Notice>{!res.passed && <div className="mt-3"><Btn kind="ghost" onClick={() => run(async () => { setSess(await api(`/cases/${id}/vcip/start`, {})); setRes(null); setAnswers({}); setGeo(null); setPhoto(null); setPan(null) })}>{x.start}</Btn></div>}</div>}
            </div>
          </Sheet>
        </>)}
    </div>
  )
}
