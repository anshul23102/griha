import { useEffect, useState } from 'react'
import { ArrowSquareOut, CheckCircle, Warning, WarningCircle, WarningOctagon } from '@phosphor-icons/react'
import { api, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Notice, Sheet, Spinner, statusCls } from '../components/kit'

function Up({ ok, demo, t }: { ok: boolean; demo: boolean; t: (k: string) => string }) {
  return ok ? <span className="inline-flex items-center gap-1 text-ok font-display font-bold"><CheckCircle size={18} weight="fill" aria-hidden />{t('ops.up')}</span>
    : demo ? <span className="font-display font-semibold text-ink2">{t('ops.absent')}</span>
    : <span className="inline-flex items-center gap-1 text-wait font-display font-bold"><WarningCircle size={18} weight="fill" aria-hidden />{t('ops.down')}</span>
}

export default function Ops() {
  const { t } = useI18n()
  const [o, setO] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let dead = false
    const go = () => api('/ops').then(x => { if (!dead) { setO(x); setErr(null) } }).catch(e => { if (!dead) setErr(e.message) })
    go(); const id = setInterval(go, 3000)
    return () => { dead = true; clearInterval(id) }
  }, [])
  if (!o) return err ? <Notice tone="bad">{err}</Notice> : <Spinner label={t('common.loading')} />
  const m = o.metrics, orch = o.orchestrator, mon = o.monitoring, m_drift: J = o.drift ?? { state: 'warming', live: 0, min_live: 100, features: [] }
  const stageMax = Math.max(1, ...Object.values<J>(m.stages).map(s => s.p95 ?? 0))
  const bars = (rows: [string, number][]) => {
    const mx = Math.max(1, ...rows.map(r => r[1]))
    return <table className="chart"><tbody>{rows.length === 0 ? <tr><td className="text-ink2">{t('ops.none')}</td></tr> : rows.map(([k, v]) => (
      <tr key={k}><th scope="row" className="font-normal mono">{k}</th><td className="w-[40%]" aria-hidden><span className="block h-3 bg-ground"><span className="block h-3 bg-blue" style={{ width: `${(v / mx) * 100}%` }} /></span></td><td className="r num font-bold">{v}</td></tr>))}</tbody></table>
  }
  return (
    <div className="flex flex-col gap-8">
      <Board hi="संचालन" en="Operations" aside={<>{t('ops.uptime', { m: Math.round(m.uptime_s / 60) })}<br />{t('ops.live')}</>}>
        <p className="m-0 mt-2 max-w-[64ch] font-medium">{t('ops.lead')}</p>
      </Board>

      {o.public_demo && (
        <Sheet title={t('ops.rec')} sub={t('ops.rec.sub')}>
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <figure className="m-0 grid gap-2"><img src="/recorded/temporal.jpg" alt={t('ops.rec.temporal.alt')} className="w-full border-2 border-rule" loading="lazy" />
              <figcaption className="text-sm text-ink2">{t('ops.rec.temporal')}</figcaption></figure>
            <figure className="m-0 grid gap-2"><img src="/recorded/grafana.png" alt={t('ops.rec.grafana.alt')} className="w-full border-2 border-rule" loading="lazy" />
              <figcaption className="text-sm text-ink2">{t('ops.rec.grafana')}</figcaption></figure>
          </div>
        </Sheet>)}

      <div className="grid gap-6 lg:grid-cols-2 items-start">
        <Sheet title={t('ops.orch')} sub={t(o.public_demo ? 'ops.orch.sub.hosted' : 'ops.orch.sub')}>
          <table className="chart"><tbody>
            <tr><th scope="row" className="font-normal">{t('ops.engine')}</th><td className="font-bold">{orch.mode === 'temporal' ? t('ops.mode.temporal') : orch.requested === 'inline' ? t('ops.mode.single') : t('ops.mode.inline')}</td></tr>
            {orch.address && <tr><th scope="row" className="font-normal">{t('ops.addr')}</th><td className="mono">{orch.address}</td></tr>}
            {orch.workflows_total !== undefined && <tr><th scope="row" className="font-normal">{t('ops.wf')}</th><td className="num">{orch.workflows_total}</td></tr>}
            <tr><th scope="row" className="font-normal">{t('ops.audit')}</th><td className="num">{o.audit_entries}</td></tr>
            <tr><th scope="row" className="font-normal">{t('ops.versions')}</th><td className="mono">policy v{o.versions.policy} {o.versions.policy_hash} · model {o.versions.model}</td></tr>
          </tbody></table>
          {orch.error && <div className="p-5 pt-0"><Notice tone="warn" title={t('ops.fallback')}>{orch.error}</Notice></div>}
        </Sheet>
        <Sheet title={t('ops.mon')} sub={t('ops.mon.sub')}>
          <table className="chart"><tbody>
            {[['Temporal UI', orch.ui, orch.mode === 'temporal'], ['Grafana', mon.grafana_url, mon.grafana], ['Prometheus', mon.prometheus_url, mon.prometheus]].map(([n, url, ok]) => (
              <tr key={String(n)}><th scope="row" className="font-bold">{n}</th><td><Up ok={!!ok} demo={!!o.public_demo} t={t} /></td><td className="r">{url && ok ? <a href={String(url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline text-blue font-display font-bold">{t('ops.open')}<ArrowSquareOut size={16} weight="bold" aria-hidden /></a> : null}</td></tr>))}
            <tr><th scope="row" className="font-bold">{t('ops.raw')}</th><td /><td className="r"><a href="/api/metrics" target="_blank" rel="noreferrer" className="underline text-blue font-display font-bold mono">/api/metrics</a></td></tr>
            <tr><th scope="row" className="font-bold">{t('ops.llm')}</th><td><Up ok={o.llm.ollama_ready} demo={!!o.public_demo} t={t} /></td><td className="r mono text-ink2">{o.llm.model}</td></tr>
          </tbody></table>
          {!(mon.grafana && mon.prometheus) && <p className="m-0 px-5 py-3 border-t border-faint text-sm text-ink2">{o.public_demo ? t('ops.hosted') : <>{t('ops.start')} <span className="mono">ops/start.sh</span></>}</p>}
        </Sheet>
      </div>

      <dl className="m-0 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 border-2 border-rule bg-sheet divide-x-2 divide-faint">
        {[[t('ops.k.decisions'), m.decisions], [t('ops.k.perMin'), m.per_minute], [t('ops.k.p50'), m.latency_ms.p50 === null ? '-' : m.latency_ms.p50 + ' ms'], [t('ops.k.p95'), m.latency_ms.p95 === null ? '-' : m.latency_ms.p95 + ' ms'],
          [t('ops.k.open'), m.reviews_open], [t('ops.k.sla'), m.sla_escalations]].map(([k, v]) => (
          <div key={String(k)} className="px-4 py-3"><dt className="text-sm text-ink2">{k}</dt><dd className="m-0 num text-2xl font-medium">{v}</dd></div>))}
      </dl>

      <div className="grid gap-6 lg:grid-cols-2 items-start">
        <Sheet title={t('ops.stages')} sub={t('ops.stages.sub')}>
          <table className="chart"><thead><tr><th>{t('ops.stage')}</th><th aria-hidden /><th className="r">p50</th><th className="r">p95</th></tr></thead><tbody>
            {Object.entries<J>(m.stages).map(([k, v]) => (
              <tr key={k}><th scope="row" className="font-normal">{t('stage.' + k)}</th><td className="w-[35%]" aria-hidden><span className="block h-3 bg-ground"><span className="block h-3 bg-ink2" style={{ width: `${((v.p95 ?? 0) / stageMax) * 100}%` }} /></span></td>
                <td className="r num">{v.p50} ms</td><td className="r num">{v.p95} ms</td></tr>))}
            {Object.keys(m.stages).length === 0 && <tr><td className="text-ink2">{t('ops.none')}</td></tr>}</tbody></table>
        </Sheet>
        <Sheet title={t('ops.outcomes')}>{bars(Object.entries<number>(m.outcomes))}
          <h3 className="px-5 pt-4 text-base font-bold">{t('ops.queues')}</h3>{bars(Object.entries<number>(m.queues))}</Sheet>
      </div>

      <div className="grid gap-6 lg:grid-cols-3 items-start">
        <Sheet title={t('ops.fraud')}>{bars(m.fraud_flags.map((f: J) => [f.code, f.count]))}</Sheet>
        <Sheet title={t('ops.rules')}>{bars(m.rules.map((f: J) => [`${f.rule} (${f.outcome})`, f.count]))}</Sheet>
        <Sheet title={t('ops.retries')} sub={t('ops.retries.sub')}>{bars(Object.entries<number>(m.activity_retries))}
          <h3 className="px-5 pt-4 text-base font-bold">{t('ops.llm.calls')}</h3>{bars(m.llm.map((l: J) => [`${l.provider} ${l.status}`, l.count]))}</Sheet>
      </div>

      <Sheet title={t('ops.drift')} sub={t('ops.drift.sub')}>
        {m_drift.state !== 'ready' ? <p className="m-0 p-5 text-ink2">{t(m_drift.state === 'warming' ? 'ops.drift.warming' : 'ops.drift.collect', { n: m_drift.live, min: m_drift.min_live })}</p> : (
          <div className="overflow-x-auto"><table className="chart min-w-[560px]">
            <thead><tr><th>{t('ops.drift.feature')}</th><th className="r">PSI</th><th>{t('desk.col.status')}</th><th className="r">{t('ops.drift.ref')}</th><th className="r">{t('ops.drift.live')}</th></tr></thead>
            <tbody>{m_drift.features.map((f: J) => {
              const o = f.status === 'stable' ? 'APPROVE' : f.status === 'shifted' ? 'REFER' : 'REJECT'
              const Icon = f.status === 'stable' ? CheckCircle : f.status === 'shifted' ? Warning : WarningOctagon
              return <tr key={f.feature}><th scope="row" className="mono font-normal">{f.feature}</th><td className="r num">{f.psi.toFixed(3)}</td>
                <td><span className={'inline-flex items-center gap-1.5 font-display font-bold ' + statusCls(o)}>{t('ops.drift.' + f.status)}<Icon size={16} weight="bold" aria-hidden /></span></td>
                <td className="r num">{f.ref_median}</td><td className="r num">{f.live_median}</td></tr>
            })}</tbody></table></div>)}
      </Sheet>
    </div>
  )
}
