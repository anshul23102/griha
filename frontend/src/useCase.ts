import { useCallback, useEffect, useState } from 'react'
import { adoptKeyFromHash, api, ApiError, type J } from './api'

/** Loads a case. While its workflow is still running it polls the real workflow progress (a Temporal query). */
export function useCase(id: string | undefined) {
  const [c, setC] = useState<J | null>(null)
  const [prog, setProg] = useState<J | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const reload = useCallback(() => setTick(x => x + 1), [])
  useEffect(() => {
    if (!id) { setC(null); setProg(null); return }
    adoptKeyFromHash(id)
    let dead = false
    let timer: ReturnType<typeof setTimeout> | undefined
    setErr(null)
    const load = async () => {
      try { const x = await api('/cases/' + id); if (!dead) { setC(x); setProg(null) } }
      catch (e) { if (e instanceof ApiError && e.status === 409) poll(); else if (!dead) setErr((e as Error).message) }
    }
    const poll = async () => {
      try {
        const p = await api('/cases/' + id + '/progress')
        if (dead) return
        setProg(p)
        if (p.state === 'done') return load()
        if (p.state === 'failed') return setErr(p.error)
        timer = setTimeout(poll, 150)
      } catch (e) { if (!dead) setErr((e as Error).message) }
    }
    if (tick === 0) { setC(null); setProg(null) }
    load()
    return () => { dead = true; if (timer) clearTimeout(timer) }
  }, [id, tick])
  return { c, prog, err, reload }
}
