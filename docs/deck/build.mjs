// Renders deck.html to ../Griha-deck.pdf (1920x1080 pages). Run from docs/deck:  python3 make.py && node build.mjs
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const { chromium } = createRequire(path.join(here, '../../frontend/package.json'))('playwright')   // playwright is a dev dependency of the frontend
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
await page.goto('file://' + path.join(here, 'deck.html'), { waitUntil: 'networkidle' })
await page.evaluate(() => document.fonts.ready)
await page.waitForTimeout(800)
// Fill each slide: the headline stays one size on every slide (hierarchy and continuity); where the content under it leaves the lower part empty, those blocks are scaled up
// with CSS zoom (the width stays, so text grows and re-wraps) until they reach the safe area.
await page.evaluate(() => {
  const SAFE = 948, MAXZ = 1.3
  document.querySelectorAll('.slide .body').forEach(b => {
    const sl = b.closest('.slide'); const sr = () => sl.getBoundingClientRect()
    const head = [...b.children].filter(e => e.matches('.kick, h1, .lede')); const blocks = [...b.children].filter(e => !e.matches('.kick, h1, .lede'))
    if (!blocks.length) return
    const bottom = els => Math.max(...els.map(e => e.getBoundingClientRect().bottom - sr().top))
    const top0 = Math.max(...head.map(e => e.getBoundingClientRect().bottom - sr().top))
    for (let k = 0; k < 5; k++) {
      const h = bottom(blocks) - top0, z = parseFloat(blocks[0].style.zoom || '1'); const target = Math.min(MAXZ, Math.max(1, z * (SAFE - top0) / h * 0.985))
      if (Math.abs(target - z) < 0.004) break
      blocks.forEach(e => { e.style.zoom = String(target) })
    }
    let z2 = parseFloat(blocks[0].style.zoom || '1')
    while (bottom(blocks) > SAFE && z2 > 1) { z2 = Math.max(1, z2 - 0.02); blocks.forEach(e => { e.style.zoom = String(z2) }) }   // reflow can overshoot: step back until it fits
  })
})
// overflow check: any element extending past its slide's content box is a layout bug
const issues = await page.evaluate(() => {
  const out = []
  document.querySelectorAll('.slide').forEach((s, i) => {
    const sr = s.getBoundingClientRect()
    s.querySelectorAll('.body, .body *').forEach(e => {
      const r = e.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) return
      if (r.bottom > sr.top + 1080 - 100 + 0.5 && !e.closest('.foot') && !e.closest('.rail') && !e.closest('.stripe')) out.push(`slide ${i + 1}: ${e.tagName}.${(e.className || '').toString().slice(0, 24)} bottom ${Math.round(r.bottom - sr.top)}`)
      if (r.right > sr.left + 1920 - 100) out.push(`slide ${i + 1}: ${e.tagName} right ${Math.round(r.right - sr.left)}`)
    })
  })
  return [...new Set(out)].slice(0, 40)
})
console.log(issues.length ? 'OVERFLOW:\n' + issues.join('\n') : 'no overflow')
await page.pdf({ path: path.join(here, '..', 'Griha-deck.pdf'), width: '1920px', height: '1080px', printBackground: true, preferCSSPageSize: true })
await browser.close()
console.log('wrote docs/Griha-deck.pdf')
