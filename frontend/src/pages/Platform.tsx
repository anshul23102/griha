import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Play } from '@phosphor-icons/react'
import { api, inr, lakh, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Notice, Sheet, Spinner, StatusWord } from '../components/kit'
import LiveDemo from '../components/LiveDemo'
import EligibilityCalc from '../components/EligibilityCalc'
import Impact from '../components/Impact'

export default function Platform() {
  const { t, tf, lang } = useI18n()
  const nav = useNavigate()
  const [stats, setStats] = useState<J | null>(null)
  const [cases, setCases] = useState<J[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const refresh = () => api('/stats').then(setStats).catch(e => setErr(e.message))
  useEffect(() => { refresh(); api('/scenarios').then(setCases).catch(e => setErr(e.message)) }, [])

  async function run(id: string) {
    setRunning(id); setErr(null)
    try { nav('/case/' + (await api('/applications?wait=false', { scenario_id: id })).case_id) } catch (e) { setErr((e as Error).message); setRunning(null) }
  }
  const ms = stats?.engine_ms_median ?? 10

  return (
    <div className="flex flex-col gap-12">
      <Board hi="गृह ऋण निर्णय मंच" en="Home-loan decision platform" aside={stats ? <>policy v{stats.policy}<br />model {stats.model}</> : undefined}>
        <p className="m-0 mt-3 max-w-[60ch] text-[1.125rem] font-medium">{t('plat.lead')}</p>
      </Board>

      <div className="grid gap-8 lg:grid-cols-[1fr_1.1fr] items-start">
        <div className="grid gap-6">
          <div className="flex flex-wrap gap-3">
            <Btn href="/apply">{t('home.cta.apply')}<ArrowRight size={18} weight="bold" aria-hidden /></Btn>
            <Btn href="/desk" kind="ghost">{t('home.cta.desk')}</Btn>
          </div>
          <section aria-labelledby="use-h">
            <h2 id="use-h" className="text-2xl font-bold mb-3">{t('use.title')}</h2>
            <ol className="list-none m-0 p-0 grid gap-2.5">
              {[1, 2, 3, 4, 5, 6].map(n => (
                <li key={n} className="flex gap-3 items-baseline"><span className="mono shrink-0 bg-ink text-sheet w-7 h-7 grid place-items-center">{n}</span><span>{t('use.' + n)}</span></li>))}
            </ol>
          </section>
        </div>
        <LiveDemo onRun={refresh} />
      </div>

      <section aria-labelledby="how-h">
        <h2 id="how-h" className="text-3xl font-bold">{t('how.title')}</h2>
        <p className="m-0 mt-1 mb-5 text-ink2 max-w-[65ch]">{t('how.sub')}</p>
        <ol className="list-none m-0 p-0 grid md:grid-cols-2 border-t-2 border-rule">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(n => (
            <li key={n} className="flex gap-4 py-5 pr-6 border-b-2 border-faint">
              <span className="plat-no shrink-0" aria-hidden>{n}</span>
              <div><h3 className="text-xl font-bold">{t(`how.${n}.t`)}</h3><p className="m-0 mt-1 text-ink2 max-w-[48ch]">{t(`how.${n}.b`)}</p></div>
            </li>))}
        </ol>
      </section>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] items-start">
        <EligibilityCalc />
        <section aria-labelledby="gain-h">
          <h2 id="gain-h" className="text-2xl font-bold mb-3">{t('gain.title')}</h2>
          <ul className="list-none m-0 p-0 border-t-2 border-rule">
            {['speed', 'why', 'policy', 'audit'].map(k => (
              <li key={k} className="py-4 border-b-2 border-faint">
                <h3 className="text-lg font-bold">{t(`gain.${k}.t`)}</h3>
                <p className="m-0 text-ink2">{t(`gain.${k}.b`, { ms: Math.round(ms) })}</p>
              </li>))}
          </ul>
          <p className="mt-4"><Link to="/coverage" className="inline-flex items-center gap-2 font-display font-bold underline text-blue">{t('nav.cover')}<ArrowRight size={18} weight="bold" aria-hidden /></Link></p>
        </section>
      </div>

      <Impact />

      {err && <Notice tone="bad">{err}</Notice>}

      <Sheet title={t('plat.prep')} sub={t('plat.prep.sub')}>
        {!cases ? <div className="p-5"><Spinner label={t('common.loading')} /></div> : (
          <div className="overflow-x-auto">
            <table className="chart min-w-[760px]">
              <thead><tr><th>#</th><th>{t('plat.col.case')}</th><th>{t('plat.col.applicant')}</th><th className="r">{t('plat.col.request')}</th><th>{t('plat.col.expected')}</th><th><span className="sr-only">{t('common.run')}</span></th></tr></thead>
              <tbody>{cases.map((c, i) => (
                <tr key={c.id}>
                  <td className="mono">P{String(i + 1).padStart(2, '0')}</td>
                  <th scope="row"><span className="block font-display font-bold text-[1.0625rem]">{tf('sc.' + c.id + '.t', c.title)}</span><span className="block text-sm text-ink2 max-w-[48ch] font-normal">{tf('sc.' + c.id + '.b', c.blurb)}</span></th>
                  <td>{c.applicant.name}<span className="block text-sm text-ink2">{c.applicant.age}, {c.applicant.city}</span></td>
                  <td className="r num">{t(c.loan.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP')} {lakh(c.loan.amount)}</td>
                  <td><StatusWord o={c.expect} /></td>
                  <td className="r"><Btn kind="ghost" onClick={() => run(c.id)} disabled={running !== null}>{running === c.id ? <Spinner /> : <Play size={16} weight="fill" aria-hidden />}{t('common.run')}</Btn></td>
                </tr>))}</tbody>
            </table>
          </div>)}
        <p className="m-0 px-5 py-3 border-t border-faint text-sm text-ink2" lang={lang}>{t('plat.prep.note')}</p>
      </Sheet>

      <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr] items-start">
        <Sheet title={t('plat.recent')} sub={t('plat.recent.sub')}>
          {!stats ? <div className="p-5"><Spinner label={t('common.loading')} /></div> : stats.recent.length === 0 ? <p className="m-0 p-5 text-ink2">{t('plat.recent.empty')}</p> : (
            <div className="overflow-x-auto"><table className="chart min-w-[520px]">
              <thead><tr><th>{t('plat.col.id')}</th><th className="r">{t('plat.col.request')}</th><th>{t('desk.col.status')}</th><th className="r">{t('plat.col.ms')}</th></tr></thead>
              <tbody>{stats.recent.map((r: J, i: number) => (
                <tr key={i}><th scope="row" className="mono">{String(i + 1).padStart(2, '0')}</th>
                  <td className="r num">{t(r.product === 'HL' ? 'ap.p.HL' : 'ap.p.LAP')} {inr(r.amount)}</td><td><StatusWord o={r.outcome} /></td><td className="r num">{r.ms} ms</td></tr>))}</tbody>
            </table></div>)}
        </Sheet>
        <Sheet title={t('plat.chart')} sub={t('plat.chart.sub')}>
          {!stats ? <div className="p-5"><Spinner label={t('common.loading')} /></div> : (
            <table className="chart"><tbody>{[[t('plat.s.cases'), stats.cases], [t('plat.s.approved'), stats.approved], [t('plat.s.referred'), stats.referred], [t('plat.s.declined'), stats.declined],
              [t('plat.s.median'), stats.engine_ms_median === null ? '-' : stats.engine_ms_median + ' ms'], [t('plat.s.audit'), stats.audit_entries]].map(([k, v]) => <tr key={String(k)}><th scope="row">{k}</th><td className="r num">{v}</td></tr>)}</tbody></table>)}
        </Sheet>
      </div>

      <section aria-labelledby="faq-h">
        <h2 id="faq-h" className="text-3xl font-bold mb-4">{t('faq.title')}</h2>
        <div className="border-t-2 border-rule">
          {[1, 2, 3, 4, 5, 6].map(n => (
            <details key={n} className="group border-b-2 border-faint">
              <summary className="list-none cursor-pointer py-4 flex items-center justify-between gap-4 text-lg font-bold hover:text-blue [&::-webkit-details-marker]:hidden">{t(`faq.${n}.q`)}<span className="mono transition-transform group-open:rotate-45 text-2xl" aria-hidden>+</span></summary>
              <p className="m-0 pb-5 text-ink2 max-w-[70ch]">{t(`faq.${n}.a`)}</p>
            </details>))}
        </div>
      </section>
    </div>
  )
}
