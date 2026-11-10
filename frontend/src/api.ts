// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type J = any

let token: string | null = localStorage.getItem('griha_token')
export const session = (): J => { try { return JSON.parse(localStorage.getItem('griha_user') || 'null') } catch { return null } }
export function setSession(u: J | null) {
  if (!u && token) void fetch('/api/logout', { method: 'POST', headers: { Authorization: 'Bearer ' + token } }).catch(() => undefined)
  token = u?.token ?? null
  try {
    if (u) { localStorage.setItem('griha_token', u.token); localStorage.setItem('griha_user', JSON.stringify(u)) }
    else { localStorage.removeItem('griha_token'); localStorage.removeItem('griha_user') }
  } catch { /* storage blocked: session lives for this page only */ }
  window.dispatchEvent(new Event('griha-auth'))
}

export class ApiError extends Error {
  status: number
  fields: Record<string, string>
  constructor(message: string, status: number, fields: Record<string, string> = {}) { super(message); this.status = status; this.fields = fields }
}

function parseDetail(detail: J, status: number): ApiError {
  if (typeof detail === 'string') return new ApiError(detail, status)
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {}
    for (const d of detail) {
      const loc = (d.loc || []).filter((x: string) => x !== 'body')
      const key = loc.length ? String(loc[loc.length - 1]) : '_'
      fields[key] = String(d.msg || 'Invalid').replace(/^Value error, /, '')
    }
    return new ApiError(Object.values(fields)[0] || 'Check the highlighted fields', status, fields)
  }
  return new ApiError('Request failed (' + status + ')', status)
}

/** Per-case access keys live in this tab's sessionStorage (never localStorage, never in a URL the server sees). */
const KEYS = 'griha_case_keys'
const keys = (): Record<string, string> => { try { return JSON.parse(sessionStorage.getItem(KEYS) || '{}') } catch { return {} } }
export const caseKey = (id: string): string | undefined => keys()[id]
export function rememberCaseKey(id: string, key: string) {
  try { sessionStorage.setItem(KEYS, JSON.stringify({ ...keys(), [id]: key })) } catch { /* storage blocked: key lives in memory only */ memKeys[id] = key }
}
const memKeys: Record<string, string> = {}
/** A shared applicant link carries the key in the URL fragment (#k=...), which browsers never send to a server. */
export function adoptKeyFromHash(id: string) {
  const m = /[#&]k=([0-9a-f]{32})/.exec(window.location.hash)
  if (m) { rememberCaseKey(id, m[1]); history.replaceState(null, '', window.location.pathname + window.location.search) }
}
export const applicantLink = (id: string): string | null => { const k = caseKey(id) ?? memKeys[id]; return k ? `${window.location.origin}/case/${id}#k=${k}` : null }

async function send(path: string, init: RequestInit): Promise<J> {
  const m = /^\/cases\/([A-Z0-9-]+)/.exec(path)
  const ck = m ? (caseKey(m[1]) ?? memKeys[m[1]]) : undefined
  const r = await fetch('/api' + path, { ...init, headers: { ...(init.headers || {}), ...(token ? { Authorization: 'Bearer ' + token } : {}), ...(ck ? { 'X-Case-Key': ck } : {}) } })
  const data = await r.json().catch(() => ({}))
  if (r.ok && data && typeof data.case_id === 'string' && typeof data.access_key === 'string') rememberCaseKey(data.case_id, data.access_key)
  if (!r.ok) {
    if (r.status === 401 && token) setSession(null)
    throw parseDetail(data.detail, r.status)
  }
  return data
}

export const api = (path: string, body?: J): Promise<J> =>
  send(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const apiForm = (path: string, form: FormData): Promise<J> => send(path, { method: 'POST', body: form })

export const inr = (n: number) => '₹' + Math.round(n).toLocaleString('en-IN')
export const lakh = (n: number) => n >= 1e7 ? '₹' + (n / 1e7).toFixed(2) + ' Cr' : '₹' + (n / 1e5).toFixed(2) + ' L'
export const pct = (n: number, d = 1) => (n * 100).toFixed(d) + '%'
