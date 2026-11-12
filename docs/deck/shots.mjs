// Captures cropped product screenshots for the deck from the running local stack (ops/start.sh). Run: node shots.mjs
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const { chromium } = createRequire(path.join(here, '../../frontend/package.json'))('playwright')
const BASE = process.env.BASE || 'http://127.0.0.1:5173'
const OUT = path.join(here, 'img') + '/'
const b = await chromium.launch({ channel: 'chrome', headless: true })
const ctx = async (theme, lang = 'en') => { const c = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 }); await c.addInitScript(([t, l]) => { try { localStorage.setItem('griha_theme', t); localStorage.setItem('griha_lang', l) } catch {} }, [theme, lang]); return c }
const mk = p => p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
// KFS in English and Hindi, light theme (it is a printable document), just the document card
for (const lang of ['en', 'hi']) {
  const c = await ctx('light', lang); const p = await c.newPage(); await p.goto(BASE + '/'); const m = await mk(p)
  await p.goto(BASE + `/case/${m.case_id}/kfs#k=${m.access_key}`); await p.locator('article.letter').waitFor(); await p.waitForTimeout(1200)
  const box = await p.locator('article.letter').boundingBox()
  await p.screenshot({ path: OUT + `kfs-${lang}.png`, clip: { x: box.x, y: box.y, width: box.width, height: Math.min(box.height, 980) } }); await c.close()
}
// element crops (night theme): each is one coherent piece of the product, wide enough to stay legible when placed in the deck
const sheet = (p, title) => p.locator('section.sheet', { has: p.locator('h2.sheet-title', { hasText: title }) }).first()
const shotEl = async (p, loc, file, maxH) => { await loc.scrollIntoViewIfNeeded(); await p.waitForTimeout(500); const bb = await loc.boundingBox(); await p.screenshot({ path: OUT + file, clip: { x: bb.x, y: bb.y, width: bb.width, height: Math.min(bb.height, maxH) } }) }
{ const c = await ctx('dark'); const p = await c.newPage(); await p.goto(BASE + '/'); const m = await mk(p)
  await p.goto(BASE + `/case/${m.case_id}#k=${m.access_key}`); await p.locator('ol.route').waitFor(); await p.waitForTimeout(1500)
  const bd = await p.locator('header.board').boundingBox()
  await p.screenshot({ path: OUT + 'case.png', clip: { x: bd.x, y: bd.y + bd.height + 36, width: bd.width, height: 430 } }); await c.close() }
{ const c = await ctx('dark'); const p = await c.newPage(); await p.goto(BASE + '/desk'); await p.getByLabel('Email').fill('admin@griha.demo'); await p.getByLabel('Password').fill('griha-demo'); await p.getByRole('button', { name: 'Sign in' }).click(); await p.getByText('Case chart').waitFor(); await p.waitForTimeout(1500)
  await shotEl(p, sheet(p, 'Case chart'), 'desk.png', 560)
  await p.goto(BASE + '/simulator'); await p.locator('#foir_cap').evaluate(el => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; s.call(el, '0.65'); el.dispatchEvent(new Event('input', { bubbles: true })) })
  await p.getByRole('button', { name: 'Replay portfolio' }).click(); await p.getByText('Portfolio impact').waitFor({ timeout: 100000 }); await p.waitForTimeout(1200)
  await shotEl(p, sheet(p, 'Portfolio impact'), 'simulator.png', 560)
  await p.goto(BASE + '/governance'); await p.getByText('Real-data check').waitFor(); await p.waitForTimeout(1200)
  await shotEl(p, sheet(p, 'Real-data check'), 'governance.png', 560)
  await c.close() }
await b.close(); console.log('wrote img/')
