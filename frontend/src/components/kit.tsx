import { useEffect, useState, type ReactNode } from 'react'
import { CheckCircle, Hourglass, WarningCircle, XCircle, X, Check } from '@phosphor-icons/react'
import { useI18n } from '../i18n'

export function Board({ hi, en, aside, children }: { hi: string; en: string; aside?: ReactNode; children?: ReactNode }) {
  const { lang } = useI18n()
  const [a, b] = lang === 'hi' ? [hi, en] : [en, hi]
  return (
    <div>
    <header className="board">
      <div className="board-inner">
        <div className="min-w-0 flex-1">
          <h1 className="l1" lang={lang === 'hi' ? 'hi' : 'en'}>{a}</h1>
          <div className="l2" lang={lang === 'hi' ? 'en' : 'hi'} aria-hidden={lang === 'hi' ? undefined : true}>{b}</div>
          {children}
        </div>
        {aside && <div className="aside">{aside}</div>}
      </div>
    </header>
    <div className="stripe" aria-hidden />
    </div>
  )
}

export type Outcome = 'APPROVE' | 'REFER' | 'REJECT'
const META: Record<Outcome, { key: string; cls: string; bg: string; Icon: typeof CheckCircle }> = {
  APPROVE: { key: 'status.approved', cls: 'text-ok', bg: 'bg-okbg', Icon: CheckCircle },
  REFER: { key: 'status.referred', cls: 'text-wait', bg: 'bg-waitbg', Icon: Hourglass },
  REJECT: { key: 'status.declined', cls: 'text-bad', bg: 'bg-badbg', Icon: XCircle },
}
export function StatusWord({ o, big }: { o: Outcome; big?: boolean }) {
  const { t } = useI18n()
  const m = META[o]
  return (
    <span className={`inline-flex items-center gap-1.5 font-display font-semibold ${m.cls} ${m.bg} ${big ? 'px-3 py-1.5 text-xl' : 'px-2 py-0.5 text-sm'} rounded-none`}>
      <m.Icon size={big ? 24 : 16} weight="fill" aria-hidden />{t(m.key)}
    </span>
  )
}
export const statusCls = (o: Outcome) => META[o].cls

export function Btn({ children, onClick, kind = 'primary', disabled, type = 'button', full, href }: {
  children: ReactNode; onClick?: () => void; kind?: 'primary' | 'ghost' | 'danger'; disabled?: boolean; type?: 'button' | 'submit'; full?: boolean; href?: string
}) {
  const k = kind === 'primary' ? 'bg-blue text-onblue border-blue hover:brightness-110'
    : kind === 'danger' ? 'bg-transparent text-bad border-bad hover:bg-badbg' : 'bg-transparent text-ink border-rule hover:bg-ground'
  const cls = `inline-flex items-center justify-center gap-2 min-h-11 px-5 rounded-none border-2 font-display font-bold text-base transition-colors disabled:opacity-45 disabled:cursor-not-allowed ${k} ${full ? 'w-full' : ''}`
  if (href) return <a href={href} className={cls}>{children}</a>
  return <button type={type} disabled={disabled} onClick={onClick} className={cls}>{children}</button>
}

export function Field({ id, label, hint, error, children }: { id: string; label: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="font-display font-semibold text-[0.9375rem]">{label}</label>
      {children}
      {hint && !error && <p id={id + '-hint'} className="text-sm text-ink2 m-0">{hint}</p>}
      {error && <p id={id + '-err'} role="alert" className="text-sm text-bad m-0 flex items-start gap-1.5"><WarningCircle size={18} weight="fill" className="mt-0.5 shrink-0" aria-hidden />{error}</p>}
    </div>
  )
}
export const inputCls = (err?: string) =>
  `w-full min-h-11 px-3 rounded-none bg-sheet text-ink border-2 ${err ? 'border-bad' : 'border-rule'} font-sans text-base placeholder:text-ink2 focus-visible:outline-[3px]`

export function Notice({ tone = 'info', children, title }: { tone?: 'info' | 'warn' | 'bad' | 'ok'; children: ReactNode; title?: string }) {
  const c = { info: 'bg-ground text-ink border-faint', warn: 'bg-waitbg text-ink border-wait', bad: 'bg-badbg text-ink border-bad', ok: 'bg-okbg text-ink border-ok' }[tone]
  return (
    <div role={tone === 'bad' ? 'alert' : 'note'} className={`rounded-none border-2 px-4 py-3 text-[0.9375rem] ${c}`}>
      {title && <div className="font-display font-semibold mb-0.5">{title}</div>}{children}
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return <span className="inline-flex items-center gap-2 text-ink2" role="status"><span className="inline-block h-4 w-4 rounded-full border-2 border-faint border-t-ink animate-spin" aria-hidden />{label}</span>
}

export function Sheet({ title, sub, children, aside }: { title?: ReactNode; sub?: ReactNode; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="sheet min-w-0">
      {(title || aside) && (
        <div className="flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b-2 border-rule">
          <div><h2 className="sheet-title">{title}</h2>{sub && <p className="m-0 mt-1 text-sm text-ink2 max-w-[65ch]">{sub}</p>}</div>
          {aside}
        </div>
      )}
      {children}
    </section>
  )
}

/** Indicator-board flap: letters settle left to right. The one authored motion. Static under reduced motion or Devanagari. */
export function Flap({ word }: { word: string }) {
  const [shown, setShown] = useState(word)
  useEffect(() => {
    setShown(word)
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce || /[^ -~]/.test(word)) return
    const chars = word.split(''); const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    let frame = 0; const total = 14
    setShown(chars.map(c => (c === ' ' ? ' ' : A[Math.floor(Math.random() * 26)])).join(''))
    const id = setInterval(() => {
      frame++
      setShown(chars.map((c, i) => (c === ' ' ? ' ' : frame > i * 1.2 + 4 ? c : A[Math.floor(Math.random() * 26)])).join(''))
      if (frame >= total + chars.length) { clearInterval(id); setShown(word) }
    }, 55)
    return () => clearInterval(id)
  }, [word])
  if (/[^\u0020-\u007e]/.test(word)) {   // Devanagari: one plate, never split conjuncts into separate flaps
    return <span className="flap" role="text"><span className="!px-3 !py-1 text-[clamp(1.5rem,5vw,2.5rem)] leading-tight">{word}</span></span>
  }
  return (
    <span className="flap text-[clamp(1.75rem,5vw,3rem)]" role="text" aria-label={word}>
      {shown.split('').map((c, i) => <span key={i} aria-hidden>{c === ' ' ? ' ' : c}</span>)}
    </span>
  )
}

export type StationState = 'wait' | 'run' | 'ok' | 'warn' | 'fail'
export function RouteStrip({ stations, label }: { stations: { key: string; label: string; state: StationState; ms?: number }[]; label: string }) {
  return (
    <ol className="route list-none m-0 p-0 flex justify-between gap-0.5 sm:gap-1 pb-1" aria-label={label}>
      <span className="track" aria-hidden />
      {stations.map((s, i) => (
        <li key={s.key} className="relative z-[1] flex flex-col items-center gap-1 sm:gap-1.5 min-w-0 flex-1">
          <span className="stn" data-state={s.state}>
            {s.state === 'ok' && <Check size={16} weight="bold" aria-hidden />}
            {s.state === 'fail' && <X size={16} weight="bold" aria-hidden />}
            {(s.state === 'wait' || s.state === 'run') && <span className="font-mono text-xs font-medium">{i + 1}</span>}
            {s.state === 'warn' && <span className="font-mono text-xs font-medium bg-yellow px-0.5">!</span>}
          </span>
          <span className="font-display font-semibold text-[0.6875rem] sm:text-[0.8125rem] leading-tight text-center text-black [overflow-wrap:normal] [word-break:keep-all]">{s.label}</span>
          <span className="hidden sm:block font-mono text-[0.6875rem] text-black/80 h-3.5">{s.ms !== undefined && s.state !== 'wait' && s.state !== 'run' ? s.ms.toFixed(0) + ' ms' : ''}</span>
          <span className="sr-only">{s.state}</span>
        </li>
      ))}
    </ol>
  )
}
