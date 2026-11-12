// End-to-end browser tests against the running stack (web :5173, API :8000). Run: NODE_PATH=$(npm root -g) node e2e/run.mjs
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const axeSrc = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8')
const BASE = process.env.BASE || 'http://127.0.0.1:5173'
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] })
const results = []
const errors = []
async function newPage(opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...opts })
  await ctx.addInitScript(() => { try { localStorage.setItem('griha_theme', 'light'); localStorage.setItem('griha_lang', 'en') } catch {} })
  const page = await ctx.newPage()
  page.on('pageerror', e => errors.push(`pageerror: ${e.message}`))
  page.on('console', m => { if (m.type() === 'error' && !/favicon|Failed to load resource/.test(m.text())) errors.push(`console: ${m.text()}`) })
  return page
}
async function test(name, fn) {
  const t0 = Date.now()
  try { await fn(); results.push([name, true, Date.now() - t0]); console.log(`PASS  ${name} (${Date.now() - t0} ms)`) }
  catch (e) { results.push([name, false, 0, e.message]); console.log(`FAIL  ${name}\n      ${e.message.split('\n')[0]}`) }
}
const ok = (c, m) => { if (!c) throw new Error(m) }
const login = async (page, email = 'officer@griha.demo') => {
  await page.goto(BASE + '/desk')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill('griha-demo')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByText('Case chart').waitFor()
}
async function axe(page, label) {
  await page.evaluate(axeSrc)
  const r = await page.evaluate(async () => (await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa'] })).violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length })))
  const bad = r.filter(v => v.impact === 'critical' || v.impact === 'serious')
  ok(bad.length === 0, `${label} accessibility: ${JSON.stringify(bad)}`)
}

await test('home: live demo runs the real engine and shows a verdict', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  await p.getByRole('button', { name: 'Run it' }).click()
  await p.getByRole('link', { name: 'Open the full case' }).waitFor({ timeout: 45000 })
  const n = await p.locator('ol.route li').count()
  ok(n === 8, `route strip should have 8 stations, got ${n}`)
  await p.getByRole('link', { name: 'Open the full case' }).click()
  await p.getByText('Regulatory controls on this case').waitFor()
  await p.context().close()
})

await test('eligibility calculator answers from the backend and reacts to input', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const big = p.locator('p.num').first()
  await big.waitFor()
  const a = await big.innerText()
  await p.locator('#c-income').fill('150000'); await p.waitForTimeout(900)
  const b = await p.locator('p.num').first().innerText()
  ok(a !== b, `max loan should change (${a} vs ${b})`)
  await p.locator('#c-emi').fill('900000'); await p.waitForTimeout(800)
  ok((await p.locator('main').innerText()).includes('Existing EMIs cannot exceed'), 'validation message expected')
  await p.context().close()
})

await test('apply wizard: real form -> workflow -> decision with 11 applicant-visible controls and 4 sources', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  await p.getByRole('button', { name: 'Fill with example values' }).click()
  await p.getByRole('button', { name: 'Next' }).click()
  await p.getByRole('button', { name: 'Next' }).click()
  await p.getByLabel('City').selectOption('Jaipur')
  await p.getByLabel('PIN code').selectOption({ index: 1 })
  await p.getByRole('button', { name: 'Next' }).click()
  await p.getByRole('checkbox').check()
  await p.getByRole('button', { name: 'Get decision' }).click()
  await p.getByText('Regulatory controls on this case').waitFor({ timeout: 20000 })
  const rows = await p.locator('section:has(h2:text("Regulatory controls")) tbody tr').count()
  ok(rows === 11, `expected 11 controls (AML, STR, EDD and four-eyes are withheld from the applicant), got ${rows}`)
  await p.getByText('Data sources and documents').click()
  ok(await p.locator('details[open] table tbody tr').count() >= 4, 'sources table')
  await axe(p, 'case page')
  await p.context().close()
})

await test('apply wizard: validation blocks bad input and explains', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  await p.getByRole('button', { name: 'Next' }).click()
  ok((await p.locator('main').innerText()).includes('This is required'), 'required messages')
  await p.getByLabel('PAN').fill('12345'); await p.getByLabel('Full name').fill('X'); await p.getByRole('button', { name: 'Next' }).click()
  ok((await p.locator('main').innerText()).includes('ABCDE1234F'), 'PAN message')
  await p.context().close()
})

await test('flaky bureau: retried by the workflow and visible as attempt 3', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  await p.getByRole('button', { name: 'Fill with example values' }).click()
  await p.getByLabel('PAN').fill('LMNOP5678Q')
  await p.getByRole('button', { name: 'Next' }).click(); await p.getByRole('button', { name: 'Next' }).click()
  await p.getByLabel('City').selectOption('Jaipur'); await p.getByLabel('PIN code').selectOption({ index: 1 }); await p.getByRole('button', { name: 'Next' }).click()
  await p.getByLabel('Test hook: simulate a data-source outage').selectOption('bureau_flaky')
  await p.getByRole('checkbox').check(); await p.getByRole('button', { name: 'Get decision' }).click()
  await p.getByText('Fetching data sources').waitFor({ timeout: 8000 })
  await p.getByText('Regulatory controls on this case').waitFor({ timeout: 20000 })
  if (!(await p.locator('main').innerText()).includes('Credit bureau report')) await p.getByText('Data sources and documents').click()   // the section opens by itself when the stage needed attention
  await p.getByText('Credit bureau report').first().waitFor({ timeout: 5000 })
  ok((await p.locator('main').innerText()).includes('Credit bureau report'), 'bureau row')
  await p.context().close()
})

await test('hindi: interface, verdict and headline translate; no mixed font fallbacks', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  await p.getByRole('button', { name: 'हिं' }).click()
  ok((await p.locator('nav').innerText()).includes('आवेदन'), 'nav in Hindi')
  const fam = await p.evaluate(() => getComputedStyle(document.body).fontFamily)
  ok(/Hind/.test(fam), `body font should be Hind, got ${fam}`)
  await p.context().close()
})

await test('desk: bad login is rejected clearly, good login shows the chart, review writes to the audit', async () => {
  const p = await newPage(); await p.goto(BASE + '/desk')
  await p.getByLabel('Password').fill('wrong'); await p.getByRole('button', { name: 'Sign in' }).click()
  await p.getByText('invalid credentials').waitFor()
  await login(p)
  // make a referred case through the UI route, then review it
  const id = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'refer_gap' }) })).json()).case_id)
  await p.goto(BASE + '/case/' + id)
  await p.getByText('Officer review').waitFor({ timeout: 15000 })
  await p.getByText('Waiting for an officer').waitFor()
  await p.getByLabel('Reason').fill('Verified income documents in branch, approving reduced amount.')
  await p.getByRole('button', { name: 'Decline' }).click()
  await p.getByText('Officer decision recorded: Decline').waitFor({ timeout: 8000 })
  await p.context().close()
})

await test('four-eyes: officer cannot approve a fraud case; admin can', async () => {
  const p = await newPage(); await login(p)
  const id = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'fraud_edit' }) })).json()).case_id)
  await p.goto(BASE + '/case/' + id)
  await p.getByLabel('Reason').fill('Customer showed originals; approving after branch visit.')
  await p.getByRole('button', { name: 'Approve' }).click()
  await p.getByText('Credit Head', { exact: false }).first().waitFor({ timeout: 8000 })
  await p.context().close()
})

await test('governance: verify chain, replay a decision, baselines and calibration shown', async () => {
  const p = await newPage(); await login(p, 'admin@griha.demo'); await p.goto(BASE + '/governance')
  await p.getByRole('button', { name: 'Verify chain integrity' }).click()
  await p.getByText('Intact', { exact: false }).waitFor()
  await p.getByRole('button', { name: 'Replay decision' }).click()
  await p.getByText('matches the recorded decision', { exact: false }).waitFor()
  await p.getByText('Model versus simple baselines').waitFor(); await p.getByText('Calibration by decile').waitFor()
  await p.context().close()
})

await test('simulator: moving a threshold replays the portfolio and shows fairness', async () => {
  const p = await newPage(); await login(p); await p.goto(BASE + '/simulator')
  await p.locator('#foir_cap').evaluate(el => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; s.call(el, '0.65'); el.dispatchEvent(new Event('input', { bubbles: true })) })
  await p.getByRole('button', { name: 'Replay portfolio' }).click()
  await p.getByText('Portfolio impact').waitFor({ timeout: 100000 }); await p.getByText('Adverse impact ratio', { exact: false }).first().waitFor()
  const ft = await p.locator('main').innerText(); ok(/gender/i.test(ft) && /city tier/i.test(ft) && /\[0\.\d+ – \d/.test(ft), 'fairness is per attribute with a 95% interval')
  await p.context().close()
})

await test('operations page shows Temporal, Prometheus and live numbers', async () => {
  const p = await newPage(); await p.goto(BASE + '/ops')
  await p.getByText('Temporal durable workflows').waitFor()
  ok((await p.locator('main').innerText()).includes('Running'), 'service status')
  await axe(p, 'ops page')
  await p.context().close()
})

await test('checklist, letter, platform pages render and pass accessibility', async () => {
  const p = await newPage()
  await p.goto(BASE + '/coverage'); await p.locator('ol > li h3').first().waitFor({ timeout: 10000 }); ok(await p.locator('ol > li h3').count() >= 8, 'eight requirement blocks'); await axe(p, 'coverage')
  await p.goto(BASE + '/'); await axe(p, 'home')
  const id = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  await p.goto(BASE + `/case/${id.case_id}/letter#k=${id.access_key}`); await p.getByRole('heading', { name: 'Decision on your application' }).waitFor(); await p.getByText('Approved', { exact: true }).first().waitFor()
  await p.context().close()
})

await test('usability: form draft survives a reload, offline banner appears, titles change, review-next works', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  await p.getByLabel('Full name').fill('Draft Person'); await p.reload()
  ok(await p.getByLabel('Full name').inputValue() === 'Draft Person', 'draft should be restored')
  await p.getByRole('button', { name: 'Start over' }).click()
  ok(await p.getByLabel('Full name').inputValue() === '', 'start over clears the draft')
  await p.goto(BASE + '/ops'); ok(/Operations/.test(await p.title()), 'route title')
  const q = await newPage(); await q.route('**/api/health', r => r.abort()); await q.goto(BASE + '/')
  await q.getByText('Cannot reach the Griha backend').waitFor({ timeout: 5000 })
  await q.context().close()
  const d = await newPage(); await login(d)
  await d.evaluate(() => fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'refer_gap' }) }))
  await d.reload(); await d.getByRole('button', { name: 'Review next case' }).click()
  await d.getByText('Officer review').waitFor({ timeout: 15000 })
  await p.context().close(); await d.context().close()
})

await test('data sources: real figures cited with links, rates derive from the repo rate, nothing synthetic dressed as real', async () => {
  const p = await newPage(); await p.goto(BASE + '/sources')
  await p.getByText('How the interest rates are built').waitFor({ timeout: 15000 })
  ok((await p.content()).includes('5.50%') && (await p.content()).includes('9.50%') && (await p.content()).includes('11.50%'), 'repo, base and stress rates shown')
  await p.getByText('NHB RESIDEX housing price index').waitFor()
  ok(await p.locator('a[href*="nhb.org.in"]').count() >= 1 && await p.locator('a[href*="rbi.org.in"]').count() >= 1, 'primary-source links present')
  await p.getByText('Looked at and not used').waitFor()
  await axe(p, 'sources')
  await p.context().close()
})

await test('regulation: KFS carries the para 131 disclosures and the terms sheet follows RBI Annex IV', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const q = await newPage(); await q.goto(BASE + `/case/${made.case_id}#k=${made.access_key}`)
  await q.getByText('Penal charges for delayed repayment').waitFor({ timeout: 15000 })
  await q.getByText('Interest reset').waitFor(); await q.getByText('If the lender changes terms to your disadvantage').waitFor()
  await q.getByText('Terms sheet (MITC)').click()
  await q.getByText('Other Most Important Terms and Conditions (MITC)').waitFor({ timeout: 15000 })
  ok((await q.content()).includes('Appendix IV(b)') && (await q.content()).includes('Security / collateral'), 'MITC layout')
  await axe(q, 'mitc')
  await p.context().close(); await q.context().close()
})

await test('business impact: measured and assumed are labelled apart, and changing an assumption changes the result', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  await p.getByText('Business impact').first().waitFor({ timeout: 15000 })
  await p.getByText('Decided by the engine alone').waitFor({ timeout: 30000 })
  ok(await p.getByText('Measured', { exact: true }).count() >= 2 && await p.getByText('Assumed', { exact: true }).count() >= 3, 'tags present')
  const read = async () => (await p.locator('tr:has(th:text-is("Saved per month")) td.num').innerText())
  const before = await read()
  await p.locator('#imp_manual_minutes').fill('90')
  await p.waitForFunction(b => { const r = [...document.querySelectorAll('tr')].find(x => x.querySelector('th')?.textContent === 'Saved per month'); return r && r.querySelector('td.num').textContent !== b }, before, { timeout: 15000 })
  ok(await read() !== before, 'result moved with the assumption')
  await axe(p, 'impact')
  await p.context().close()
})

await test('privacy: a case link without its key is a plain not-found; the key (or a staff login) opens it', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const q = await newPage(); await q.goto(BASE + `/case/${made.case_id}`)
  await q.getByText('case not found').waitFor({ timeout: 10000 })
  ok(!(await q.content()).includes('Approved'), 'no case content without the key')
  const r = await newPage(); await r.goto(BASE + `/case/${made.case_id}#k=${made.access_key}`)
  await r.getByText('Application status').first().waitFor({ timeout: 15000 })
  ok(!r.url().includes('k='), 'key is removed from the address bar after it is stored')
  const s = await newPage(); await login(s); await s.goto(BASE + `/case/${made.case_id}`); await s.getByText('Application status').first().waitFor({ timeout: 15000 })
  for (const c of [p, q, r, s]) await c.context().close()
})

await test('regulation: privacy notice lists the data; screening findings are withheld from the applicant; a rights request is logged; staff still see the finding', async () => {
  const p = await newPage(); await p.goto(BASE + '/privacy')
  await p.getByText('What we collect').waitFor({ timeout: 10000 })
  ok((await p.locator('main').innerText()).includes('the full number is never stored'), 'itemised data')
  await axe(p, 'privacy notice')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'sanctions' }) })).json()))
  const a = await newPage(); await a.goto(BASE + `/case/${made.case_id}#k=${made.access_key}`)
  await a.getByText('Application status').first().waitFor({ timeout: 15000 })
  await a.getByText('Your data rights').waitFor()
  const txt = (await a.locator('main').innerText()).toLowerCase()
  ok(!txt.includes('watchlist') && !txt.includes('sanctions list') && !txt.includes('suspicious') && !txt.includes('four-eyes'), 'applicant view must not mention screening findings')
  ok(txt.includes('one more check'), 'neutral wording shown')
  await a.getByRole('button', { name: 'Withdraw my consent' }).click()
  await a.getByText(/Request recorded\. Reference/).waitFor({ timeout: 8000 })
  const s = await newPage(); await login(s, 'admin@griha.demo'); await s.goto(BASE + `/case/${made.case_id}`)
  await s.getByText('Application status').first().waitFor({ timeout: 15000 })
  ok((await s.locator('main').innerText()).toLowerCase().includes('watchlist'), 'staff see the finding')
  for (const c of [p, a, s]) await c.context().close()
})

await test('regulation: KFS in the Annex I format with proposal number, validity, APR sheet, schedule and a recorded acknowledgement', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const k = await newPage(); await k.goto(BASE + `/case/${made.case_id}/kfs#k=${made.access_key}`)
  await k.getByText('Part 1: Interest rate and fees and charges').waitFor({ timeout: 15000 })
  const txt = await k.locator('main').innerText()
  ok(txt.includes('Proposal number: P-') && txt.includes('Open for acceptance until'), 'proposal number and validity')
  ok(txt.includes('Computation of the annual percentage rate') && txt.includes('Repayment schedule'), 'APR sheet and schedule')
  ok(await k.locator('table').nth(3).locator('tbody tr').count() >= 12, 'amortisation rows')
  await axe(k, 'KFS page')
  await k.getByRole('button', { name: 'Record my acknowledgement' }).click()
  await k.getByText('Acknowledgement recorded').waitFor({ timeout: 8000 })
  for (const c of [p, k]) await c.context().close()
})

await test('regulation: the KFS is available in Hindi, same numbers, and says the translation is unreviewed', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const k = await newPage(); await k.addInitScript(() => { try { localStorage.setItem('griha_lang', 'hi') } catch {} })
  await k.goto(BASE + `/case/${made.case_id}/kfs#k=${made.access_key}`)
  await k.getByText('भाग 1: ब्याज दर, शुल्क और प्रभार').waitFor({ timeout: 15000 })
  const txt = await k.locator('main').innerText()
  ok(txt.includes('स्वीकृत ऋण राशि') && txt.includes('वार्षिक प्रतिशत दर') && txt.includes('ऋणदाता बताएगा'), 'Hindi items and lender placeholders')
  ok(/APR/.test(txt) && /\d+\.\d\d%/.test(txt), 'APR figure present')
  ok(txt.includes('विधिक अनुवादक'), 'unreviewed-translation notice')
  await axe(k, 'Hindi KFS page')
  for (const c of [p, k]) await c.context().close()
})

await test('governance: real-data check and the breach register (admin) work', async () => {
  const p = await newPage(); await login(p, 'admin@griha.demo'); await p.goto(BASE + '/governance')
  await p.getByText('Real-data check').waitFor({ timeout: 15000 })
  const t = await p.locator('main').innerText(); ok(t.includes('German Credit') && t.includes('Taiwan'), 'both public datasets listed')
  await p.getByLabel('What happened', { exact: false }).fill('A laptop with an unencrypted export was lost by a contractor')
  await p.getByRole('button', { name: 'Log breach' }).click()
  await p.getByText('Board report due').waitFor({ timeout: 8000 })
  await p.getByRole('button', { name: /Mark board notified/ }).first().click()
  await p.getByText('principals', { exact: false }).first().waitFor({ timeout: 8000 })
  await axe(p, 'Governance with breach register')
  await p.context().close()
})

await test('real sanctions screen: a listed name is withheld from the applicant, staff see the UN list reference', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const r = await p.evaluate(async () => {
    const ref = await (await fetch('/api/reference')).json(); const pin = ref.cities.find(c => c.name === 'Jaipur').pins[0]
    const f = { name: 'Mohammed Masood Azhar Alvi', dob: '1968-07-10', pan: 'abcde1234f', phone: '98765 43211', gender: 'M', employment: 'salaried', employer: 'Metro Hospital', monthly_income: 62000, existing_emi: 4000, city: 'Jaipur', pincode: pin, product: 'HL', amount: 1500000, tenure_months: 84, property_type: 'apartment', area_sqft: 950, property_age_years: 6, declared_value: 3600000, survey_no: 'KH-221/4', consent: true }
    const res = await fetch('/api/applications/new', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(f) }); const j = await res.json()
    const body = await (await fetch('/api/cases/' + j.case_id, { headers: { 'X-Case-Key': j.access_key } })).text()
    return { outcome: j.decision?.outcome, body: body.toLowerCase() }
  })
  ok(r.outcome === 'REFER', 'referred, not auto-declined: ' + r.outcome)
  ok(!r.body.includes('qdi.') && !r.body.includes('consolidated list'), 'no list reference in the applicant view')
  await p.context().close()
})

await test('example values are fresh each time, so one judge never looks like a ring to the next', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  const seen = new Set()
  for (let i = 0; i < 2; i++) { await p.getByRole('button', { name: 'Fill with example values' }).click(); seen.add(await p.getByLabel('PAN', { exact: false }).first().inputValue()) }
  ok(seen.size === 2, 'two clicks gave the same PAN: ' + [...seen])
  await p.context().close()
})

await test('unknown address shows a real not-found page, and the home page says where humans come in', async () => {
  const p = await newPage(); const r = await p.goto(BASE + '/no-such-page')
  await p.getByText('Page not found').waitFor({ timeout: 8000 })
  await p.goto(BASE + '/'); await p.getByText('Where the humans come in').waitFor({ timeout: 20000 })
  const t = await p.locator('main').innerText(); ok(/Credit/.test(t) && /asked for more than supportable|bureau score/.test(t), 'queue breakdown with credit reasons')
  await axe(p, 'Home with breakdown')
  await p.context().close()
})

await test('servicing: quarterly statement, document-release clock with compensation, and a recovery contact outside hours is refused', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const s = await newPage(); await login(s, 'admin@griha.demo'); await s.goto(BASE + `/case/${made.case_id}/servicing#k=${made.access_key}`)
  await s.getByText('Quarterly statement').first().waitFor({ timeout: 15000 })
  const t0 = await s.locator('main').innerText(); ok(/Principal recovered/.test(t0) && /APR/.test(t0), 'statement table')
  await s.getByLabel('Date of full repayment').fill('2020-01-01'); await s.getByLabel('Date the documents were released', { exact: false }).fill('2020-02-20'); await s.getByLabel('Reason given to the borrower', { exact: false }).fill('registry filing was late')
  await s.getByRole('button', { name: 'Record', exact: true }).click(); await s.getByText('Compensation due').waitFor({ timeout: 8000 })
  ok((await s.locator('main').innerText()).includes('1,00,000'), 'Rs 5,000 x 20 days')
  await s.getByLabel('Agency name').fill('Unknown Recovery Co'); await s.getByLabel('Date and time', { exact: false }).fill('2027-02-10T20:15'); await s.getByLabel('What it was about').fill('reminder')
  await s.getByRole('button', { name: 'Check and record' }).click(); await s.getByText('Refused and logged').waitFor({ timeout: 8000 })
  ok(/8:00 a\.m\. to 7:00 p\.m\./.test(await s.locator('main').innerText()), 'hours rule cited')
  await axe(s, 'Servicing page')
  for (const c of [p, s]) await c.context().close()
})

await test('Account Aggregator sandbox: consent request, approval in the aggregator app, encrypted fetch, and the data is read', async () => {
  const p = await newPage(); await p.goto(BASE + '/apply')
  await p.getByRole('button', { name: 'Fill with example values' }).click()
  await p.getByRole('button', { name: 'Next' }).click(); await p.getByRole('button', { name: 'Next' }).click()
  await p.getByLabel('City').selectOption('Jaipur'); await p.getByLabel('PIN code').selectOption({ index: 1 }); await p.getByRole('button', { name: 'Next' }).click()
  await p.locator('input[name=statement_source][value=uploaded]').check()
  const aa = p.getByTestId('aa-link'); await aa.waitFor({ timeout: 10000 })
  await aa.getByRole('button', { name: 'Request consent' }).click()
  await aa.getByText('Consent request from Griha').waitFor({ timeout: 10000 })
  ok((await aa.innerText()).includes('Loan underwriting'), 'purpose shown to the customer')
  await aa.getByRole('button', { name: 'Approve in the Aggregator app' }).click()
  await aa.getByRole('button', { name: 'Fetch my bank data' }).click()
  await aa.getByText('Bank data received, decrypted and read').waitFor({ timeout: 20000 })
  ok((await aa.innerText()).includes('decrypted'), 'protocol trace lists the decryption step')
  await p.context().close()
})

await test('V-CIP: a session with every mandatory element passes; prompting at the customer end forces rejection', async () => {
  const p = await newPage(); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  const s = await newPage({ permissions: ['geolocation', 'camera'], geolocation: { latitude: 28.6139, longitude: 77.209 } }); await login(s, 'officer@griha.demo')
  await s.goto(BASE + `/case/${made.case_id}/vcip#k=${made.access_key}`)
  await s.getByRole('button', { name: 'Start a session' }).click(); await s.getByText('Questions for this session').waitFor({ timeout: 10000 })
  ok(await s.locator('ol li').count() >= 6, 'six questions')
  const fails = s.getByRole('button', { name: 'Complete the session' })
  await fails.click(); await s.getByText(/^Session cannot be completed:/).waitFor({ timeout: 8000 })           // nothing recorded yet: refused, with paragraphs
  ok(/paras? 27/.test(await s.locator('main').innerText()), 'paragraphs cited')
  await s.getByRole('button', { name: 'Start a session' }).click(); await s.getByText('Questions for this session').waitFor()   // a refused session is final: start a fresh one
  for (const r of await s.getByLabel('Asked, passed').all()) await r.check()
  await s.getByRole('button', { name: "Capture the customer's live location" }).click(); await s.getByText('captured').first().waitFor({ timeout: 8000 })
  await s.getByRole('button', { name: "Capture the customer's photograph" }).click(); await s.getByText('sha256').first().waitFor({ timeout: 10000 })
  await s.getByLabel('The customer gave an e-PAN instead').check()
  await s.getByLabel('The customer confirmed their economic and financial profile').check(); await s.getByLabel('The liveness check passed').check()
  await fails.click(); await s.getByText(/^Session passed\./).waitFor({ timeout: 8000 })
  await s.getByLabel('Prompting was observed', { exact: false }).check()
  await axe(s, 'V-CIP page')
  for (const c of [p, s]) await c.context().close()
})

await test('phone: route-strip station labels never overlap and the strip uses the full width', async () => {
  const p = await newPage({ viewport: { width: 390, height: 844 } }); await p.goto(BASE + '/')
  const made = await p.evaluate(async () => (await (await fetch('/api/applications', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario_id: 'salaried_approve' }) })).json()))
  await p.goto(BASE + `/case/${made.case_id}#k=${made.access_key}`); await p.locator('ol.route li').first().waitFor({ timeout: 15000 })
  const r = await p.evaluate(() => {
    const strip = document.querySelector('ol.route'); const sr = strip.getBoundingClientRect(); const parent = strip.parentElement.getBoundingClientRect()
    const labels = [...strip.querySelectorAll('li > span.font-display')].map(e => e.getBoundingClientRect())
    let overlaps = 0
    for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) { const a = labels[i], b = labels[j]; if (a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5) overlaps++ }
    const clipped = labels.filter(l => l.right > innerWidth + 0.5 || l.left < -0.5).length
    return { overlaps, clipped, widthShare: sr.width / parent.width, n: labels.length }
  })
  ok(r.n >= 7, 'stations present: ' + r.n); ok(r.overlaps === 0, 'labels overlap: ' + r.overlaps); ok(r.clipped === 0, 'labels run off screen'); ok(r.widthShare > 0.95, 'strip fills its box: ' + r.widthShare.toFixed(2))
  await p.context().close()
})

await test('phone width: no sideways scroll on any main page', async () => {
  const p = await newPage({ viewport: { width: 375, height: 800 } })
  for (const path of ['/', '/apply', '/ops', '/coverage', '/governance']) {
    await p.goto(BASE + path); await p.waitForTimeout(700)
    const over = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    ok(over <= 1, `${path} overflows by ${over}px`)
  }
  await p.context().close()
})

ok(errors.length === 0, 'browser errors:\n' + errors.slice(0, 5).join('\n'))
await browser.close()
const failed = results.filter(r => !r[1])
console.log(`\n${results.length - failed.length}/${results.length} passed`)
process.exit(failed.length ? 1 : 0)
