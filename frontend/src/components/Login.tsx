import { useState } from 'react'
import { api, setSession } from '../api'
import { useI18n } from '../i18n'
import { Board, Btn, Field, inputCls, Notice, Sheet, Spinner } from './kit'

export default function Login({ hi, en }: { hi: string; en: string }) {
  const { t } = useI18n()
  const [email, setEmail] = useState('officer@griha.demo')
  const [pw, setPw] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  async function go(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErr(null)
    try { setSession(await api('/login', { email, password: pw })) } catch (x) { setErr((x as Error).message) }
    setBusy(false)
  }
  return (
    <div className="flex flex-col gap-6">
      <Board hi={hi} en={en} />
      <div className="max-w-xl">
        <Sheet title={t('login.title')} sub={t('login.sub')}>
          <form onSubmit={go} className="p-5 grid gap-5">
            <Field id="email" label={t('login.email')}><input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} className={inputCls()} autoComplete="username" /></Field>
            <Field id="pw" label={t('login.pw')} error={err ?? undefined}><input id="pw" type="password" value={pw} onChange={e => setPw(e.target.value)} className={inputCls(err ?? undefined)} autoComplete="current-password" aria-describedby={err ? 'pw-err' : undefined} /></Field>
            <Btn type="submit" disabled={busy || !pw}>{busy && <Spinner />}{t('login.go')}</Btn>
            <Notice title={t('login.demo.t')}>{t('login.demo.b')}</Notice>
          </form>
        </Sheet>
      </div>
    </div>
  )
}
