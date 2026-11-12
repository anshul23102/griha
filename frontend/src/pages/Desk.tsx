import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, session, inr, type J } from '../api'
import { useI18n } from '../i18n'
import Login from '../components/Login'
import { Board, Notice, Sheet, Spinner, StatusWord } from '../components/kit'

export default function Desk() {
  const { t, tc, lang } = useI18n()
  const nav = useNavigate()
  const [user, setUser] = useState(session())
  const [rows, setRows] = useState<J[] | null>(null)
  const [stats, setStats] = useState<J | null>(null)
  const [f, setF] = useState('REFER')
  const [active, setActive] = useState(0)
  const [err, setErr] = useState<string | null>(null)
  const body = useRef<HTMLDivElement>(null)
  useEffect(() => { const h = () => setUser(session()); window.addEventListener('griha-auth', h); return () => window.removeEventListener('griha-auth', h) }, [])
  useEffect(() => {
    if (!user) return
    setErr(null)
    api('/cases').then(setRows).catch(e => setErr(e.message))
    api('/stats').then(setStats).catch(() => {})
  }, [user])
  if (!user) return <Login hi="ऋणदाता डेस्क" en="Lender desk" />

  const shown = (rows ?? []).filter(r => f === 'ALL' || (f === 'REFER' && r.outcome === 'REFER') || r.outcome === f)
  const tabs: [string, string][] = [['REFER', t('desk.f.refer')], ['REJECT', t('desk.f.declined')], ['APPROVE', t('desk.f.approved')], ['ALL', t('desk.f.all')]]
  const count = (k: string) => (rows ?? []).filter(r => k === 'ALL' || r.outcome === k).length
  const key = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(shown.length - 1, a + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(0, a - 1)) }
    else if (e.key === 'Enter' && shown[active]) nav('/case/' + shown[active].case_id)
  }

  return (
    <div className="flex flex-col gap-6">
      <Board hi="ऋणदाता डेस्क" en="Lender desk" aside={<>{user.email ?? user.name}<br />{t('role.' + user.role)}{stats && stats.engine_ms_median !== null && <><br />{t('desk.median')} {stats.engine_ms_median} ms</>}</>}>
        <p className="m-0 mt-2 font-medium max-w-[60ch]">{t('desk.lead')}</p>
      </Board>
      {err && <Notice tone="bad">{err}</Notice>}
      <Sheet title={t('desk.chart')} sub={t('desk.chart.sub')}
        aside={<div className="flex gap-2 flex-wrap justify-end items-center"><button onClick={() => { const n = (rows ?? []).find(r => r.outcome === 'REFER' && r.status === 'in_review'); if (n) nav('/case/' + n.case_id) }} disabled={!(rows ?? []).some(r => r.outcome === 'REFER' && r.status === 'in_review')} className="min-h-10 px-3 font-display font-bold bg-blue text-onblue disabled:opacity-45">{(rows ?? []).some(r => r.outcome === 'REFER' && r.status === 'in_review') ? t('desk.next') : t('desk.next.none')}</button><div role="group" aria-label={t('desk.filter')} className="flex gap-1 flex-wrap justify-end">
          {tabs.map(([k, l]) => <button key={k} aria-pressed={f === k} onClick={() => { setF(k); setActive(0) }}
            className={`min-h-10 px-3 font-display font-semibold border-2 rounded-none ${f === k ? 'bg-yellow text-black border-black' : 'border-faint hover:bg-ground'}`}>{l} <span className="num">{count(k)}</span></button>)}</div></div>}>
        {!rows ? <div className="p-5"><Spinner label={t('common.loading')} /></div> : shown.length === 0 ? (
          <div className="p-8 text-ink2">{t('desk.empty')}</div>
        ) : (
          <div ref={body} tabIndex={0} onKeyDown={key} className="overflow-x-auto outline-offset-[-3px]" aria-label={t('desk.kbd')}>
            <table className="chart min-w-[760px]">
              <thead><tr><th>{t('desk.col.case')}</th><th>{t('plat.col.applicant')}</th><th className="r">{t('plat.col.request')}</th><th>{t('desk.col.status')}</th><th>{t('desk.col.queue')}</th><th>{t('desk.col.fraud')}</th><th>{t('desk.col.why')}</th></tr></thead>
              <tbody>{shown.map((r, i) => (
                <tr key={r.case_id} data-active={i === active} onClick={() => nav('/case/' + r.case_id)} className="cursor-pointer hover:bg-ground">
                  <th scope="row"><Link to={'/case/' + r.case_id} onClick={e => e.stopPropagation()} className="mono underline text-blue">{r.case_id}</Link></th><td>{r.name}</td><td className="r num">{t(r.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP')} {inr(r.amount)}</td>
                  <td><StatusWord o={r.outcome} />{r.status.includes('officer') && <span className="block text-xs text-ink2">{t('act.' + (r.status.startsWith('approved') ? 'approve' : r.status.startsWith('declined') ? 'decline' : 'request_documents'))}</span>}</td>
                  <td>{r.queue ? t('queue.' + r.queue) : '-'}</td><td>{r.fraud ? t('fraud.' + r.fraud) : '-'}</td>
                  <td className="text-ink2 max-w-[34ch]">{lang === 'hi' ? [t(r.outcome === 'APPROVE' ? 'status.approved' : r.outcome === 'REFER' ? 'status.referred' : 'status.declined'), r.top_code ? tc(r.top_code) : ''].filter(Boolean).join(': ') : r.headline}</td>
                </tr>))}</tbody>
            </table>
          </div>)}
        <p className="m-0 px-5 py-3 border-t border-faint text-sm text-ink2">{t('desk.kbd.hint')}</p>
      </Sheet>
    </div>
  )
}
