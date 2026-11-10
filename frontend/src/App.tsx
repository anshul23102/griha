import { Component, Suspense, lazy, useEffect, useState, type ReactNode } from 'react'
import { NavLink, Route, Routes, Link, useLocation } from 'react-router-dom'
import { Moon, Sun, SignOut } from '@phosphor-icons/react'
import { api, session, setSession } from './api'
import { useI18n } from './i18n'
import Platform from './pages/Platform'

const navCls = ({ isActive }: { isActive: boolean }) =>
  'px-3 min-h-10 inline-flex items-center rounded-none font-display font-semibold text-[0.9375rem] whitespace-nowrap ' +
  (isActive ? 'bg-yellow text-black' : 'text-white hover:bg-white/15')

class Boundary extends Component<{ children: ReactNode; title: string; body: string; label: string }, { err: boolean }> {
  state = { err: false }
  static getDerivedStateFromError() { return { err: true } }
  render() {
    if (!this.state.err) return this.props.children
    return (
      <div role="alert" className="sheet p-6 max-w-xl">
        <h2 className="sheet-title">{this.props.title}</h2><p className="mt-2">{this.props.body}</p>
        <button onClick={() => location.reload()} className="mt-4 min-h-11 px-5 bg-blue text-onblue font-display font-bold">{this.props.label}</button>
      </div>
    )
  }
}

function useTheme() {
  const read = () => document.documentElement.dataset.theme as 'light' | 'dark' | undefined
  const [theme, setTheme] = useState<'light' | 'dark'>(() => read() ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))
  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('griha_theme', next) } catch { /* ignore */ }
    setTheme(next)
  }
  return { theme, toggle }
}

const Apply = lazy(() => import('./pages/Apply'))
const Case = lazy(() => import('./pages/Case'))
const Letter = lazy(() => import('./pages/Letter'))
const Mitc = lazy(() => import('./pages/Mitc'))
const Desk = lazy(() => import('./pages/Desk'))
const Simulator = lazy(() => import('./pages/Simulator'))
const Governance = lazy(() => import('./pages/Governance'))
const Ops = lazy(() => import('./pages/Ops'))
const Coverage = lazy(() => import('./pages/Coverage'))
const Sources = lazy(() => import('./pages/Sources'))
const Privacy = lazy(() => import('./pages/Privacy'))
const Kfs = lazy(() => import('./pages/Kfs'))
function NotFound() {
  const { t } = useI18n()
  useEffect(() => { document.title = '404 | Griha' }, [])
  return (
    <div className="mx-auto max-w-[640px] py-16 grid gap-4">
      <h1 className="m-0 text-3xl font-bold">{t('nf.title')}</h1>
      <p className="m-0 text-ink2">{t('nf.body')}</p>
      <p className="m-0"><Link to="/" className="underline text-blue font-display font-bold">{t('nf.home')}</Link></p>
    </div>
  )
}

export default function App() {
  const { t, lang, setLang } = useI18n()
  const { theme, toggle } = useTheme()
  const [user, setUser] = useState(session())
  const loc = useLocation()
  useEffect(() => { const f = () => setUser(session()); window.addEventListener('griha-auth', f); return () => window.removeEventListener('griha-auth', f) }, [])
  useEffect(() => { window.scrollTo(0, 0) }, [loc.pathname])
  const letter = loc.pathname.endsWith('/letter') || loc.pathname.endsWith('/mitc')
  const [offline, setOffline] = useState(false)
  const [demo, setDemo] = useState(false)
  useEffect(() => {
    let dead = false
    const ping = () => api('/health').then(h => { if (!dead) { setOffline(false); setDemo(!!h.public_demo) } }).catch(() => { if (!dead) setOffline(true) })
    ping(); const id = setInterval(ping, 8000)
    return () => { dead = true; clearInterval(id) }
  }, [])
  useEffect(() => {
    const seg = loc.pathname.split('/')[1] || 'platform'
    document.title = t('title.' + (['platform', 'apply', 'case', 'desk', 'simulator', 'governance', 'ops', 'coverage', 'sources'].includes(seg) ? seg : 'platform'))
  }, [loc.pathname, lang])

  return (
    <div className="min-h-dvh flex flex-col">
      {!letter && (
        <>
          <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 bg-yellow text-black px-3 py-2 rounded-none no-print">{t('common.skip')}</a>
          <div className="bg-black no-print">
            <div className="mx-auto max-w-[1240px] px-4 py-2 flex flex-wrap items-center gap-x-5 gap-y-1">
              <Link to="/" className="inline-flex items-center gap-2 bg-yellow text-black rounded-none px-2.5 py-1 font-display font-bold leading-none" aria-label="Griha">
                <span lang="hi" className="text-lg">गृह</span><span className="text-lg">Griha</span>
              </Link>
              <nav aria-label={t('nav.label')} className="flex gap-1 overflow-x-auto order-3 sm:order-none w-full sm:w-auto -mx-1 px-1 py-0.5">
                <NavLink to="/" end className={navCls}>{t('nav.platform')}</NavLink>
                <NavLink to="/apply" className={navCls}>{t('nav.apply')}</NavLink>
                <NavLink to="/desk" className={navCls}>{t('nav.desk')}</NavLink>
                <NavLink to="/simulator" className={navCls}>{t('nav.sim')}</NavLink>
                <NavLink to="/governance" className={navCls}>{t('nav.gov')}</NavLink>
                <NavLink to="/ops" className={navCls}>{t('nav.ops')}</NavLink>
                <NavLink to="/sources" className={navCls}>{t('nav.sources')}</NavLink>
                <NavLink to="/coverage" className={navCls}>{t('nav.cover')}</NavLink>
              </nav>
              <div className="ml-auto flex items-center gap-2">
                <div role="group" aria-label={t('common.language')} className="inline-flex border-2 border-white/60 rounded-none overflow-hidden">
                  {(['en', 'hi'] as const).map(l => (
                    <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l} lang={l}
                      className={`min-h-9 px-2.5 font-display font-semibold text-sm ${lang === l ? 'bg-white text-black' : 'text-white hover:bg-white/15'}`}>{l === 'en' ? 'EN' : 'हिं'}</button>
                  ))}
                </div>
                <button onClick={toggle} aria-label={t(theme === 'dark' ? 'common.light' : 'common.dark')} title={t(theme === 'dark' ? 'common.light' : 'common.dark')}
                  className="min-h-9 w-9 grid place-items-center border-2 border-white/60 rounded-none text-white hover:bg-white/15">
                  {theme === 'dark' ? <Sun size={18} weight="bold" aria-hidden /> : <Moon size={18} weight="bold" aria-hidden />}
                </button>
                {user && (
                  <button onClick={() => setSession(null)} aria-label={t('nav.signout')} title={`${user.email} (${user.role})`}
                    className="min-h-9 px-2 inline-flex items-center gap-1.5 text-white font-display font-semibold text-sm hover:bg-white/15 rounded-none">
                    <SignOut size={18} weight="bold" aria-hidden /><span className="hidden sm:inline">{user.name}</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}
      {demo && !letter && <div role="note" className="bg-waitbg text-ink border-b-2 border-wait px-4 py-2 text-center font-medium no-print">{t('app.demo')}</div>}
      {offline && !letter && <div role="alert" className="bg-badbg text-ink border-b-2 border-bad px-4 py-2 text-center font-medium no-print">{t('app.offline')}</div>}
      <main id="main" className={letter ? 'flex-1' : 'flex-1 mx-auto w-full max-w-[1240px] px-4 py-6 sm:py-8'}>
        <Boundary title={t('app.crash')} body={t('app.crash.b')} label={t('app.reload')} key={loc.pathname}>
        <Suspense fallback={<div className="py-12" role="status" aria-live="polite">{t('common.loading')}</div>}>
        <Routes>
          <Route path="/" element={<Platform />} />
          <Route path="/apply" element={<Apply />} />
          <Route path="/case/:id" element={<Case />} />
          <Route path="/case/:id/letter" element={<Letter />} />
          <Route path="/case/:id/mitc" element={<Mitc />} />
          <Route path="/case/:id/kfs" element={<Kfs />} />
          <Route path="/desk" element={<Desk />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/governance" element={<Governance />} />
          <Route path="/ops" element={<Ops />} />
          <Route path="/coverage" element={<Coverage />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
        </Boundary>
      </main>
      {!letter && <footer className="no-print mx-auto w-full max-w-[1240px] px-4 pb-8 text-sm text-ink2">{t('common.synthetic')} <Link to="/privacy" className="underline">{t('nav.privacy')}</Link></footer>}
    </div>
  )
}
