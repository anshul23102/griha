import { useEffect, useState } from 'react'
import { ArrowSquareOut, CheckCircle, Clock, Gear, Prohibit, Robot } from '@phosphor-icons/react'
import { api, type J } from '../api'
import { useI18n } from '../i18n'
import { Board, Notice, Sheet, Spinner } from '../components/kit'

const GROUPS: [string, string][] = [['real', 'src.g.real'], ['secondary', 'src.g.secondary'], ['pending', 'src.g.pending'], ['synthetic', 'src.g.synthetic'], ['internal', 'src.g.internal'], ['rejected', 'src.g.rejected']]

function Status({ s }: { s: string }) {
  const { t } = useI18n()
  const map: Record<string, [typeof CheckCircle, string]> = {
    verified: [CheckCircle, 'text-ok'], pending: [Clock, 'text-wait'], synthetic: [Robot, 'text-ink2'], internal: [Gear, 'text-ink2'], rejected: [Prohibit, 'text-bad'],
  }
  const [Icon, cls] = map[s] ?? map.internal
  return <span className={'inline-flex items-center gap-1.5 font-display font-bold ' + cls}>{t('src.s.' + s)}<Icon size={16} weight="bold" aria-hidden /></span>
}

export default function Sources() {
  const { t } = useI18n()
  const [d, setD] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api('/sources').then(setD).catch(e => setErr(e.message)) }, [])
  if (!d) return err ? <Notice tone="bad">{err}</Notice> : <Spinner label={t('common.loading')} />
  const r = d.rates
  return (
    <div className="flex flex-col gap-8">
      <Board hi="डेटा स्रोत" en="Data sources" aside={<>{t('src.retrieved', { d: d.retrieved })}</>}>
        <p className="m-0 mt-2 max-w-[64ch] font-medium">{t('src.lead')}</p>
      </Board>

      <Sheet title={t('src.rates')} sub={t('src.rates.sub')}>
        <table className="chart"><tbody>
          <tr><th scope="row" className="font-normal">{t('src.rate.repo')}</th><td className="r num">{r.repo_pct.toFixed(2)}%</td><td className="text-ink2">{t('src.rate.repo.n')}</td></tr>
          <tr><th scope="row" className="font-normal">{t('src.rate.spread')}</th><td className="r num">+ {r.spread_pct.toFixed(2)}%</td><td className="text-ink2">{t('src.rate.spread.n')}</td></tr>
          <tr><th scope="row" className="font-bold">{t('src.rate.base')}</th><td className="r num font-bold">{r.base_pct.toFixed(2)}%</td><td className="text-ink2">{t('src.rate.base.n')}</td></tr>
          <tr><th scope="row" className="font-normal">{t('src.rate.buffer')}</th><td className="r num">+ {r.stress_buffer_pct.toFixed(2)}%</td><td className="text-ink2">{t('src.rate.spread.n')}</td></tr>
          <tr><th scope="row" className="font-bold">{t('src.rate.stress')}</th><td className="r num font-bold">{r.stress_pct.toFixed(2)}%</td><td className="text-ink2">{t('src.rate.stress.n')}</td></tr>
        </tbody></table>
      </Sheet>

      {GROUPS.map(([g, label]) => {
        const items = d.items.filter((i: J) => i.group === g)
        if (!items.length) return null
        return (
          <Sheet key={g} title={t(label)} sub={t(label + '.sub')}>
            <ul className="m-0 p-0 list-none divide-y-2 divide-faint">
              {items.map((i: J) => (
                <li key={i.id} className="px-5 py-4 grid gap-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <h3 className="m-0 text-lg font-bold">{i.name}</h3><Status s={i.status} />
                  </div>
                  <p className="m-0 text-sm text-ink2">{i.publisher}{i.as_of ? ` · ${i.as_of}` : ''}{i.retrieved ? ` · ${t('src.retrieved.short', { d: i.retrieved })}` : ''}</p>
                  <p className="m-0 font-medium">{i.value}</p>
                  <p className="m-0 max-w-[80ch]">{i.detail}</p>
                  <p className="m-0 max-w-[80ch] text-ink2"><strong className="font-semibold">{t('src.used')}</strong> {i.used_for}</p>
                  {i.url && <a href={i.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 w-fit underline text-blue font-display font-bold">{t('src.open')}<ArrowSquareOut size={16} weight="bold" aria-hidden /></a>}
                </li>))}
            </ul>
          </Sheet>)
      })}
    </div>
  )
}
