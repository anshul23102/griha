// Captures the README screenshots from the running stack. Run: NODE_PATH=$(npm root -g) node e2e/shots.mjs   (stack: ops/start.sh)
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = process.env.BASE || 'http://127.0.0.1:5173'
const OUT = new URL('../../docs/img/', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const ctxOf = async (w = 1440, h = 900, lang = 'en', theme = 'dark') => {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 })
  await ctx.addInitScript(([l, t]) => { try { localStorage.setItem('griha_theme', t); localStorage.setItem('griha_lang', l) } catch {} }, [lang, theme])
  return ctx
}
const settle = p => p.waitForTimeout(900)
const shot = async (p, name, full = false) => { await settle(p); await p.screenshot({ path: OUT + name, fullPage: full }); console.log('wrote', name) }
const mk = async p => p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
const login = async (p, email) => {
  await p.goto(BASE + '/desk'); await p.getByLabel('Email').fill(email); await p.getByLabel('Password').fill('griha-demo')
  await p.getByRole('button', { name: 'Sign in' }).click(); await p.getByText('Case chart').waitFor()
}

let c = await ctxOf(); let p = await c.newPage()
await p.goto(BASE + '/'); await p.waitForTimeout(1500); await shot(p, 'home.png')
await p.goto(BASE + '/'); await p.getByRole('button', { name: /Run|run/ }).first().click().catch(() => {}); await p.waitForTimeout(3500); await shot(p, 'home-live.png', true)
const made = await mk(p)
await p.goto(BASE + `/case/${made.case_id}#k=${made.access_key}`); await p.waitForTimeout(2000); await shot(p, 'case.png')
await p.goto(BASE + `/case/${made.case_id}/kfs#k=${made.access_key}`); await p.getByText('Part 1').waitFor(); await shot(p, 'kfs.png')
await p.goto(BASE + '/coverage'); await shot(p, 'coverage.png')
await p.goto(BASE + '/sources'); await shot(p, 'sources.png')
await p.goto(BASE + '/privacy'); await shot(p, 'privacy.png')
await c.close()

c = await ctxOf(1440, 900, 'hi'); p = await c.newPage()
const m2 = await mk((await p.goto(BASE + '/'), p))
await p.goto(BASE + `/case/${m2.case_id}/kfs#k=${m2.access_key}`); await p.getByText('भाग 1').waitFor(); await shot(p, 'kfs-hi.png')
await c.close()

c = await ctxOf(); p = await c.newPage(); await login(p, 'admin@griha.demo')
await p.goto(BASE + '/governance'); await p.getByText('Real-data check').waitFor(); await shot(p, 'governance.png', true)
await p.goto(BASE + '/ops'); await p.waitForTimeout(2500); await shot(p, 'ops.png')
await p.goto(BASE + '/simulator'); await p.locator('#foir_cap').evaluate(el => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; s.call(el, '0.65'); el.dispatchEvent(new Event('input', { bubbles: true })) }); await p.getByRole('button', { name: 'Replay portfolio' }).click(); await p.getByText('Portfolio impact').waitFor({ timeout: 100000 }); await shot(p, 'simulator.png', true)
await p.goto(BASE + '/desk'); await p.waitForTimeout(1500); await shot(p, 'desk.png')
await c.close()

c = await ctxOf(390, 844); p = await c.newPage(); const m3 = await mk((await p.goto(BASE + '/'), p))
await p.goto(BASE + `/case/${m3.case_id}#k=${m3.access_key}`); await p.waitForTimeout(2000); await shot(p, 'mobile-case.png')
await c.close(); await browser.close()
