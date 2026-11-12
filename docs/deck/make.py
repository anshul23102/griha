"""Builds docs/deck/deck.html (the Griha submission deck) from the slide bodies below. Render to PDF with build.mjs.

Design system, kept the same on every slide so the deck reads as one object:
- Grid: 1920x1080, 120 px side margins, a 12-column layout, an 8 px baseline rhythm.
- Hierarchy: one headline per slide (72 px, 700), a lede (32 px, muted), body (27 px+), captions (21 px). Numbers are the loudest thing on a slide that has them.
- Continuity: the top rail names the station and shows the eight-station route with the current one filled, the footer carries the page number, and the same
  yellow/black/paper palette and square corners as the product ("The Reservation Chart").
- Colour: yellow is only for the thing to look at; blue for links and the live system; green/amber/red only for status, never decoration.
"""
from __future__ import annotations

import html
from pathlib import Path

OUT = Path(__file__).parent / "deck.html"
LIVE = "https://d3l1fg79dbflis.cloudfront.net"
REPO = "https://github.com/anshul23102/griha"
STATIONS = ["Data", "Income", "Property", "Eligibility", "Policy", "Risk", "Fraud", "Compliance"]

CSS = """
@font-face{font-family:Hind;font-weight:400;src:url(fonts/hind-latin-400-normal.woff2);unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:Hind;font-weight:500;src:url(fonts/hind-latin-500-normal.woff2);unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:Hind;font-weight:600;src:url(fonts/hind-latin-600-normal.woff2);unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:Hind;font-weight:700;src:url(fonts/hind-latin-700-normal.woff2);unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:Hind;font-weight:400;src:url(fonts/hind-devanagari-400-normal.woff2);unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF}
@font-face{font-family:Hind;font-weight:600;src:url(fonts/hind-devanagari-600-normal.woff2);unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF}
@font-face{font-family:Hind;font-weight:700;src:url(fonts/hind-devanagari-700-normal.woff2);unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF}
@font-face{font-family:Azeret;font-weight:400;src:url(fonts/azeret-mono-latin-400-normal.woff2)}
@font-face{font-family:Azeret;font-weight:500;src:url(fonts/azeret-mono-latin-500-normal.woff2)}
@font-face{font-family:Azeret;font-weight:600;src:url(fonts/azeret-mono-latin-600-normal.woff2)}
:root{--ink:#121212;--paper:#F7F4EA;--card:#FFFFFF;--yellow:#FFC21A;--blue:#12439A;--ok:#0E7A3E;--wait:#A64600;--bad:#B3141B;--mute:#55554F;--faint:#D9D4C4}
@page{size:1920px 1080px;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#888}
body{font-family:Hind,sans-serif;color:var(--ink);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.slide{width:1920px;height:1080px;position:relative;overflow:hidden;background:var(--paper);padding:176px 120px 128px;break-after:page;page-break-after:always}
.slide.dark{background:var(--ink);color:#F7F4EA}
.mono{font-family:Azeret,monospace}
/* rail (top) and footer (bottom): the continuity layer */
.rail{position:absolute;left:120px;right:120px;top:56px;height:72px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid var(--ink)}
.dark .rail{border-color:#F7F4EA}
.rail .tag{font-family:Azeret;font-size:21px;letter-spacing:.06em;text-transform:uppercase;font-weight:500}
.rail .tag b{background:var(--yellow);color:var(--ink);padding:3px 12px;margin-right:14px;font-weight:600}
.route{display:flex;align-items:center;gap:0}
.route i{display:block;width:26px;height:26px;border:3px solid var(--ink);border-radius:50%;background:var(--paper);position:relative}
.dark .route i{border-color:#F7F4EA;background:var(--ink)}
.route i.on{background:var(--yellow);border-color:var(--ink);width:34px;height:34px}
.route i.done{background:var(--ink)}
.dark .route i.done{background:#F7F4EA}
.route u{display:block;width:26px;height:3px;background:var(--ink)}
.dark .route u{background:#F7F4EA}
.foot{position:absolute;left:120px;right:120px;bottom:44px;height:48px;display:flex;align-items:center;justify-content:space-between;font-family:Azeret;font-size:19px;color:var(--mute);border-top:2px solid var(--faint)}
.dark .foot{color:#B8B4A6;border-color:#3A3A36}
.foot .pg{color:var(--ink);font-weight:600}.dark .foot .pg{color:#F7F4EA}
h1{font-size:58px;line-height:1.08;font-weight:700;letter-spacing:-.01em;max-width:1640px}
h2{font-size:34px;line-height:1.15;font-weight:700}
h3{font-size:28px;line-height:1.2;font-weight:700}
.lede{font-size:28px;line-height:1.4;color:var(--mute);margin-top:16px;max-width:1500px}
.dark .lede{color:#CFCABB}
p,li{font-size:24px;line-height:1.42}
.cap{font-size:20px;line-height:1.38;color:var(--mute)}
.kick{font-family:Azeret;font-size:20px;letter-spacing:.08em;text-transform:uppercase;color:var(--blue);font-weight:600;margin-bottom:10px}
.dark .kick{color:var(--yellow)}
.body{position:absolute;left:120px;right:120px;top:160px;bottom:128px}
.cols{display:grid;gap:48px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:repeat(3,1fr)}.c4{grid-template-columns:repeat(4,1fr)}.c58{grid-template-columns:5fr 7fr}.c75{grid-template-columns:7fr 5fr}
.card{background:var(--card);border:3px solid var(--ink);padding:26px 30px}
.card.y{background:var(--yellow)}.card.k{background:var(--ink);color:#F7F4EA}
.stat{font-family:Hind;font-weight:700;font-size:92px;line-height:1;letter-spacing:-.02em}
.stat small{font-size:38px;letter-spacing:0;margin-left:4px}
.lab{font-size:22px;line-height:1.3;margin-top:10px}
ul.l{list-style:none}ul.l li{position:relative;padding-left:32px;margin-bottom:10px}
ul.l li::before{content:"";position:absolute;left:0;top:.62em;width:16px;height:16px;background:var(--ink)}
.dark ul.l li::before{background:var(--yellow)}
ul.l.y li::before{background:var(--yellow);border:3px solid var(--ink);width:16px;height:16px}
table{border-collapse:collapse;width:100%;font-size:22px}
th{font-family:Azeret;font-size:17px;text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:8px 12px;border-bottom:3px solid var(--ink);font-weight:600}
td{padding:9px 12px;border-bottom:2px solid var(--faint);vertical-align:top;line-height:1.3}
td.n,th.n{text-align:right;font-family:Azeret}
.tag2{display:inline-block;font-family:Azeret;font-size:18px;font-weight:600;padding:3px 12px;border:3px solid var(--ink);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
.t-real{background:#CFEBD9;color:#075B2D;border-color:#075B2D}.t-sim{background:#FFE3B8;color:#7A3A00;border-color:#7A3A00}.t-no{background:#fff;color:var(--ink)}
.stripe{height:26px;background:repeating-linear-gradient(135deg,#121212 0 22px,#FFC21A 22px 44px)}
.shot{border:3px solid var(--ink);overflow:hidden;background:#111}.shot img{width:100%;height:100%;object-fit:cover;object-position:top left;display:block}
.num{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:50%;background:var(--ink);color:var(--yellow);font-family:Azeret;font-weight:600;font-size:26px;flex:none}
.big{font-size:38px;line-height:1.2;font-weight:600}
.row{display:flex;gap:24px;align-items:flex-start}
.mt8{margin-top:8px}.mt16{margin-top:14px}.mt24{margin-top:20px}.mt32{margin-top:24px}.mt48{margin-top:32px}
.ok{color:var(--ok)}.bad{color:var(--bad)}.wait{color:var(--wait)}.blue{color:var(--blue)}
.arrow{font-family:Azeret;font-size:44px;font-weight:600;align-self:center}
.bar{display:flex;height:56px;border:3px solid var(--ink)}.bar div{display:flex;align-items:center;justify-content:center;font-family:Azeret;font-weight:600;font-size:23px}
a{color:inherit}
table.tight td{padding:6px 12px}
table.tight .tag2{font-size:15px;padding:1px 8px;border-width:2px}
"""


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def route(current: int | None) -> str:
    if current is None:
        return ""
    parts = []
    for i in range(8):
        cls = "on" if i == current else ("done" if i < current else "")
        parts.append(f'<i class="{cls}"></i>')
        if i < 7:
            parts.append("<u></u>")
    return f'<div class="route" aria-label="Station {current + 1} of 8">{"".join(parts)}</div>'


SLIDES: list[str] = []


def slide(body: str, *, tag: str, num: str = "", station: int | None = None, dark: bool = False) -> None:
    n = len(SLIDES) + 1
    rail = f'<div class="rail"><div class="tag"><b>{n:02d}</b>{esc(tag)}</div>{route(station)}</div>' if tag else ""
    SLIDES.append(f'<section class="slide{" dark" if dark else ""}">{rail}{body}'
                  f'<div class="foot"><span>गृह Griha · Hero Housing Fintech Challenge · Problem Statement 2</span><span class="pg">{n:02d} / @@TOTAL@@</span></div></section>')


# ------------------------------------------------------------------ 1 title
SLIDES.append(f"""<section class="slide dark" style="padding:0">
<div style="position:absolute;left:120px;right:120px;top:120px;bottom:150px;background:var(--yellow);border:6px solid #121212;color:#121212;padding:72px 84px;display:flex;flex-direction:column;justify-content:space-between;outline:3px solid #F7F4EA;outline-offset:-3px">
  <div class="mono" style="font-size:23px;letter-spacing:.08em;text-transform:uppercase;font-weight:600">Hero Housing Fintech Challenge · Problem Statement 2 · i-Hack · IIT Bombay E-Summit 2026</div>
  <div>
    <div style="font-size:172px;line-height:1;font-weight:700;letter-spacing:-.02em;margin-top:12px">गृह Griha</div>
    <div style="font-size:50px;line-height:1.2;font-weight:600;margin-top:36px;max-width:1380px">Automated mortgage underwriting you can explain, replay and defend to a regulator.</div>
    <div style="font-size:30px;line-height:1.4;margin-top:24px;max-width:1300px">Home Loan and Loan Against Property decisions in about ten milliseconds: approve, reject or refer, with reasons, a Key Facts Statement in the RBI's own format, and a compliance trail built from the primary texts.</div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:flex-end;font-size:26px;line-height:1.5">
    <div><b>Live demo</b> &nbsp;<a class="mono" style="font-size:23px" href="{LIVE}">{LIVE.replace("https://", "")}</a><br><b>Code</b> &nbsp;<a class="mono" style="font-size:23px" href="{REPO}">github.com/anshul23102/griha</a></div>
    <div style="text-align:right"><b>Anshul Jain</b> · IIIT-Delhi<br>All applicant data is synthetic</div>
  </div>
</div>
<div class="stripe" style="position:absolute;left:120px;right:120px;bottom:114px;height:22px"></div>
<div class="foot" style="color:#B8B4A6;border-color:#3A3A36;bottom:36px"><span>Submission deck</span><span class="pg" style="color:#F7F4EA">01 / @@TOTAL@@</span></div>
</section>""")

# ------------------------------------------------------------------ 2 problem
slide("""<div class="body">
<div class="kick">The problem</div>
<h1>A home loan should not wait days for an answer nobody can explain.</h1>
<div class="cols c3 mt48">
  <div class="card"><h3>Slow</h3><p class="mt16">A Home Loan or LAP file passes through people for data checks, policy checks, fraud and KYC review, property review and sign-off.</p></div>
  <div class="card"><h3>Opaque</h3><p class="mt16">When a decision is made, the reasons live in notes and memory. An auditor cannot replay it, and an applicant cannot learn what to change.</p></div>
  <div class="card"><h3>Heavily regulated</h3><p class="mt16">RBI's Fair Practices Code, Digital Lending, KYC and Responsible Business Conduct Directions and the DPDP Rules all bind every single file.</p></div>
</div>
<div class="card k mt48" style="display:flex;gap:36px;align-items:center">
  <div class="big" style="flex:none;width:520px;color:var(--yellow)">What PS2 asks for</div>
  <div style="font-size:24px;line-height:1.45">A fully automated, regulator-compliant underwriting engine for Home Loans and LAP, covering eight capabilities: data integration, eligibility and policy, fraud and KYC/AML, risk scoring, documents and property, compliance, an instant approve / reject / refer decision, and explainability with governance.</div>
</div>
</div>""", tag="Context", num="01")

# ------------------------------------------------------------------ 3 answer
slide(f"""<div class="body">
<div class="kick">Our answer</div>
<h1>Griha decides the clear cases alone and shows its work on every case.</h1>
<div class="lede">Language models read documents. They never decide. Every outcome comes from a hashed rulebook and a calibrated, monotone risk model.</div>
<div class="cols c4 mt48">
  <div class="card y"><div class="stat">10<small>ms</small></div><div class="lab">median engine time per decision on a laptop</div></div>
  <div class="card"><div class="stat">62.5<small>%</small></div><div class="lab">of 1,000 synthetic cases decided with no person involved</div></div>
  <div class="card"><div class="stat">19</div><div class="lab">policy rules as code, plus 15 compliance controls on every case</div></div>
  <div class="card"><div class="stat">4</div><div class="lab">regulatory texts read in their primary form, paragraph by paragraph</div></div>
</div>
<div class="cols c3 mt32">
  <div><h3>Explainable</h3><p class="cap mt8" style="font-size:22px">Reasons, evidence behind each, a replayable record, and a Path to Yes for fixable cases.</p></div>
  <div><h3>Regulator-aware</h3><p class="cap mt8" style="font-size:22px">Controls cite their paragraph and say how far we verified them. The Key Facts Statement matches RBI Annex I.</p></div>
  <div><h3>Honest</h3><p class="cap mt8" style="font-size:22px">Synthetic data is labelled. We show a real-data check, the limits, and what is not built.</p></div>
</div>
</div>""", tag="Overview", num="02")

# ------------------------------------------------------------------ 4 flow
names = ["Data", "Income", "Property", "Eligibility", "Policy", "Risk", "Fraud + KYC/AML", "Compliance"]
lines = ["Bank, bureau, KYC, land records, fetched in parallel", "Twelve months of credits become a verified income", "Valuation range, comparables, title, valuation reports",
         "FOIR at a stress rate, LTV caps, tenure, counter-offer", "19 hashed rules, each with a reason", "Calibrated default probability, drivers, price", "Tamper checks, UN list screen, linked applicants", "15 controls with clause and status"]
st = "".join(f'<div class="card" style="padding:22px 24px"><div class="num">{i+1}</div><h3 style="font-size:27px;margin-top:14px">{n}</h3><p class="cap mt8" style="font-size:21px">{l}</p></div>' for i, (n, l) in enumerate(zip(names, lines)))
slide(f"""<div class="body">
<div class="kick">End to end</div>
<h1>One application becomes one decision through eight stations.</h1>
<div class="cols mt48" style="grid-template-columns:repeat(8,1fr);gap:16px;position:relative">{st}</div>
<div class="row mt48" style="align-items:stretch">
  <div class="card" style="flex:1"><div class="kick" style="margin:0">In</div><p style="font-size:22px">Four-step form, a PDF bank statement, or Account Aggregator data in the ReBIT format. Consent is recorded first.</p></div>
  <div class="arrow">→</div>
  <div class="card k" style="flex:1.2"><div class="kick" style="margin:0;color:var(--yellow)">Decision in about 10 ms</div><p style="font-size:22px">An outcome, an offer, reasons, a Key Facts Statement and an audit entry holding the encrypted input.</p></div>
  <div class="arrow">→</div>
  <div class="card" style="flex:1.4"><div class="kick" style="margin:0">Out</div><p style="font-size:22px"><b class="ok">APPROVE</b> with offer · <b class="bad">REJECT</b> with reasons · <b class="wait">REFER</b> to a Credit, Fraud, Property or Data queue, evidence ready.</p></div>
</div>
</div>""", tag="PS2 flow", num="03", station=0)

# ------------------------------------------------------------------ 5 data
slide("""<div class="body">
<div class="kick">Requirement 1 of 8 · Integrate data sources</div>
<h1>Four sources feed the engine, and a missing one is never guessed.</h1>
<div class="cols c2 mt48" style="gap:64px">
  <div>
    <table><thead><tr><th>Source</th><th>Channel</th><th>Status</th></tr></thead><tbody>
      <tr><td>Bank statement</td><td>PDF parser, or ReBIT DEPOSIT FI file (XML or JSON)</td><td><span class="tag2 t-real">Real parser</span></td></tr>
      <tr><td>Credit bureau</td><td>Simulated, shaped like a bureau report</td><td><span class="tag2 t-sim">Simulated</span></td></tr>
      <tr><td>KYC and sanctions</td><td>Simulated KYC; real UN list screen</td><td><span class="tag2 t-real">UN list real</span></td></tr>
      <tr><td>Land records</td><td>Simulated title, RERA, encumbrance</td><td><span class="tag2 t-sim">Simulated</span></td></tr>
    </tbody></table>
  </div>
  <div>
    <ul class="l">
      <li>All four are fetched <b>in parallel</b> by a Temporal workflow with retries. Every case shows each source's channel, time, record count and the stages it feeds.</li>
      <li>If a source stays down the case goes to the <b>Data queue</b>. Nothing is guessed. Try the <i>flaky bureau</i> test in the demo: the workflow retries and succeeds on attempt 3.</li>
      <li>The Account Aggregator parser reads the public ReBIT schema, rejects DTDs and entities, caps size and sanitises narrations.</li>
      <li>Documents are checked for balance continuity, holder match and text addressed to an AI reviewer.</li>
    </ul>
  </div>
</div>
</div>""", tag="Data", num="04", station=0)

# ------------------------------------------------------------------ 6 policy
slide("""<div class="body">
<div class="kick">Requirement 2 of 8 · Eligibility and policy</div>
<h1>Credit policy is code: hashed, traced, and testable before it ships.</h1>
<div class="cols c58 mt48" style="gap:56px">
  <div>
    <h3>Eligibility sizing</h3>
    <table class="mt16"><thead><tr><th>Housing loan up to</th><th class="n">Max LTV</th></tr></thead><tbody>
      <tr><td>₹30 lakh</td><td class="n">90%</td></tr><tr><td>₹30 to ₹75 lakh</td><td class="n">80%</td></tr><tr><td>Above ₹75 lakh</td><td class="n">75%</td></tr><tr><td>LAP (internal limit)</td><td class="n">60%</td></tr>
    </tbody></table>
    <p class="cap mt16">Housing caps are RBI HFC Directions 2025, para 58. FOIR is tested at a stress rate; tenure caps 30 years (HL) and 15 (LAP). A smaller counter-offer replaces a flat no.</p>
  </div>
  <div>
    <h3>Policy Impact Simulator: replay 1,000 stored applications before changing a rule</h3>
    <table class="mt16"><thead><tr><th>FOIR cap 55% → 65%</th><th class="n">Now</th><th class="n">Proposed</th></tr></thead><tbody>
      <tr><td>Auto-approved</td><td class="n">53.8%</td><td class="n ok">58.8%</td></tr><tr><td>Referred to officers</td><td class="n">37.5%</td><td class="n">32.9%</td></tr>
      <tr><td>Expected loss on approved</td><td class="n">3.12%</td><td class="n bad">3.42%</td></tr><tr><td>Realised default (synthetic truth)</td><td class="n">3.35%</td><td class="n bad">4.08%</td></tr>
    </tbody></table>
    <p class="cap mt16">The 19 rules live in one YAML file whose hash is stored with every decision. The simulator shows the gain and the cost together, and a fairness check per attribute with a 95% interval.</p>
  </div>
</div>
</div>""", tag="Eligibility and policy", num="05", station=4)

# ------------------------------------------------------------------ 7 fraud
slide("""<div class="body">
<div class="kick">Requirement 3 of 8 · Fraud detection and KYC/AML</div>
<h1>Fraud and AML checks run on every case, and the law decides what the applicant sees.</h1>
<div class="cols c3 mt48">
  <div class="card"><h3>Detect</h3><ul class="l mt16" style="font-size:22px"><li>Balance-arithmetic and edit checks on statements</li><li>Round-trip money and window dressing</li><li>Cash intensity and an STR signal</li><li>Linked-applicant graph: shared phone, property, rings</li><li>Behaviour anomaly model</li></ul></div>
  <div class="card"><h3>Screen</h3><div class="stat mt16">1,007</div><div class="lab">entries on the real UN Security Council Consolidated List (snapshot 10 Nov 2026), names and aliases</div><p class="cap mt16">A close match is a possible match. It goes to an officer: it is never an automatic decline (KYC Directions para 18).</p></div>
  <div class="card y"><h3>Withhold</h3><p class="mt16" style="font-size:22px">Fraud findings, sanctions matches, the STR signal and the risk category are removed from the applicant's view (KYC paras 19, 20(4), 52). Officers see everything.</p><div class="card mt16" style="padding:16px 20px;background:#fff"><div class="mono" style="font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)">What the applicant is told</div><p style="font-size:21px;margin-top:6px">"Your application needs one more check by an officer. We will contact you on your registered number."</p></div></div>
</div>
<p class="cap mt32">On 120 injected fraud cases (edited statements, window dressing, identity mismatch, rings) 119 were held back. The typologies are ones we wrote; real fraud differs. Aadhaar is treated as voluntary; a missing e-KYC refers to an officer.</p>
</div>""", tag="Fraud + KYC/AML", num="06", station=6)

# ------------------------------------------------------------------ 8 risk
slide("""<div class="body">
<div class="kick">Requirement 4 of 8 · Risk scoring</div>
<h1>A monotone, calibrated model, checked on real borrowers outside our own generator.</h1>
<div class="row mt32" style="gap:14px;align-items:stretch">
  <div class="card" style="flex:1.3;padding:16px 20px"><b>12 inputs</b><p class="cap" style="font-size:18px">FOIR, LTV, bureau score, income variability, buffer, delinquency, enquiries, bounces, age, tenure and more</p></div><div class="arrow">→</div>
  <div class="card" style="flex:1;padding:16px 20px"><b>5 bagged LightGBM</b><p class="cap" style="font-size:18px">monotone constraints: worse never lowers risk</p></div><div class="arrow">→</div>
  <div class="card" style="flex:1;padding:16px 20px"><b>Isotonic calibration</b><p class="cap" style="font-size:18px">so 3% means about 3%</p></div><div class="arrow">→</div>
  <div class="card" style="flex:1;padding:16px 20px"><b>Conformal range</b><p class="cap" style="font-size:18px">80% band; uncertain cases refer</p></div><div class="arrow">→</div>
  <div class="card y" style="flex:1;padding:16px 20px"><b>SHAP reasons + scorecard</b><p class="cap" style="color:#121212;font-size:18px">650 points at 30:1; band A to E sets the price</p></div>
</div>
<div class="cols c2 mt32" style="gap:48px">
  <div><h3>Synthetic test set (720 held out)</h3>
    <table class="mt16"><thead><tr><th>Measure</th><th class="n">Value</th></tr></thead><tbody>
      <tr><td>AUC · KS · Brier</td><td class="n">0.747 · 0.414 · 0.058</td></tr><tr><td>Plain logistic regression AUC</td><td class="n wait">0.760</td></tr><tr><td>Mean predicted vs actual default</td><td class="n">7.3% vs 6.0%</td></tr></tbody></table><p class="cap mt8">The boosted model does not beat logistic regression on this synthetic data. We say so, and keep it for the monotone guarantee and SHAP.</p></div>
  <div><h3>Real borrowers (UCI, CC BY 4.0), 5-fold out of sample</h3>
    <table class="mt16"><thead><tr><th>Dataset</th><th class="n">Logit</th><th class="n">Free</th><th class="n">Monotone</th></tr></thead><tbody>
      <tr><td>German Credit, 1,000</td><td class="n">0.782</td><td class="n">0.793</td><td class="n"><b>0.788</b></td></tr><tr><td>Taiwan cards, 30,000</td><td class="n">0.723</td><td class="n">0.783</td><td class="n"><b>0.782</b></td></tr>
    </tbody></table><p class="cap mt8">AUC. The constraints cost almost no ranking power; calibration gaps are 1.1% and 0.4%. Not Indian mortgages: it shows the recipe, not Indian accuracy.</p></div>
</div>
</div>""", tag="Risk scoring", num="07", station=5)

# ------------------------------------------------------------------ 9 documents & property
slide("""<div class="body">
<div class="kick">Requirement 5 of 8 · Documents and property</div>
<h1>Documents are verified and the property is assessed inside the same flow.</h1>
<div class="cols c2 mt48" style="gap:64px">
  <div><h3>Documents</h3>
  <ul class="l mt16"><li>Bank statement as a PDF, or Account Aggregator data. Both become the same object, so every downstream check works unchanged.</li>
  <li>Text-layer parser by default; an optional local model reads through a typed, validated schema and is cross-checked against the PDF.</li>
  <li><b>Injection-safe:</b> a sentence addressed to an AI reviewer inside a document is treated as evidence of tampering and never obeyed.</li>
  <li>The verification table shows PAN, Aadhaar e-KYC, statement and land record with method and status.</li></ul></div>
  <div><h3>Property</h3>
  <table class="mt16"><thead><tr><th>Valuation model (synthetic)</th><th class="n">Result</th></tr></thead><tbody>
    <tr><td>Median absolute error</td><td class="n">6.3%</td></tr><tr><td>Within 10% of true value</td><td class="n">80.3%</td></tr><tr><td>80% interval actually covers</td><td class="n wait">73.9%</td></tr></tbody></table>
  <p class="cap mt8">The interval is narrower than its label; we show that, not hide it. Price levels are synthetic.</p>
  <ul class="l mt16" style="font-size:22px"><li>Quantile valuation, comparables, circle rate, title, RERA, encumbrance flags.</li><li>Loans from ₹50 lakh need two valuation reports; from ₹75 lakh two independent ones, and the lower value is used (HFC Directions Annex V).</li></ul></div>
</div>
</div>""", tag="Documents and property", num="08", station=2)

# ------------------------------------------------------------------ 10 compliance
slide("""<div class="body">
<div class="kick">Requirement 6 of 8 · Compliance checks</div>
<h1>Five regulatory documents, read in their primary text, drive the controls.</h1>
<table class="mt32" style="font-size:22px"><thead><tr><th style="width:34%">Document</th><th>What it changed in the product</th></tr></thead><tbody>
  <tr><td><b>RBI HFC Directions 2025</b><br><span class="cap">Fair Practices Code, Annexes IV, V</span></td><td>LTV caps (para 58), KFS disclosures (131), two valuation reports, grievance route with the NHB cell (144), foreclosure (163), terms sheet</td></tr>
  <tr><td><b>RBI Digital Lending Directions 2025</b></td><td>Cooling-off period, grievance escalation to RBI after 30 days, data kept in India</td></tr>
  <tr><td><b>RBI NBFC KYC Directions 2025</b></td><td>Aadhaar voluntary, officer records any rejection, high-risk rating for online onboarding, tipping-off secrecy, five-year retention</td></tr>
  <tr><td><b>RBI Responsible Business Conduct 2025</b></td><td>Annex I Key Facts Statement, 3-working-day validity, penal charge is not interest (para 30), prepayment (34)</td></tr>
  <tr><td><b>DPDP Rules 2025</b><br><span class="cap">G.S.R. 846(E)</span></td><td>Privacy notice, safeguards, data-principal rights with a 90-day clock, breach register with the 72-hour deadline</td></tr>
</tbody></table>
<div class="cols c2 mt24" style="gap:32px"><div class="card y" style="padding:20px 28px"><p style="font-size:22px"><b>"NHB regulations":</b> since August 2019 the RBI regulates housing finance companies; its 2025 HFC Directions are the operative text. The NHB complaint cell still appears in the borrower's letter.</p></div>
<div class="card" style="padding:20px 28px"><p style="font-size:22px"><b>Reading found real defects, now fixed:</b> the applicant view leaked sanctions findings; PAN or sanctions failures auto-declined; erasure ignored the five-year retention duty.</p></div></div>
</div>""", tag="Compliance", num="09", station=7)

# ------------------------------------------------------------------ 11 KFS
slide("""<div class="body">
<div class="kick">Key Facts Statement</div>
<h1>The offer comes with a statement in the RBI's own Annex I layout, in English and Hindi.</h1>
<div class="cols mt32" style="grid-template-columns:6fr 6fr 4fr;gap:28px;align-items:start">
  <div class="shot" style="height:auto"><img src="img/kfs-en.png" alt="Key Facts Statement in English" style="height:auto;object-fit:initial"></div>
  <div class="shot" style="height:auto"><img src="img/kfs-hi.png" alt="Key Facts Statement in Hindi" style="height:auto;object-fit:initial"></div>
  <div style="display:flex;flex-direction:column;justify-content:space-between">
    <ul class="l" style="font-size:22px"><li>Proposal number, and validity of at least three working days</li><li>Part 1 rate and fees, Part 2 qualitative items</li><li>APR computation sheet and the full repayment schedule</li><li>Effect of a 25 bps rate change</li><li>Borrower acknowledgement recorded in the audit log</li></ul>
    <div class="card y" style="padding:20px 24px"><div class="stat" style="font-size:64px">17.07%</div><p class="cap" style="color:#121212;font-size:21px">Our APR reproduces the RBI's worked example: ₹20,000 at 15% for 24 months with ₹400 fees. It is a permanent test.</p></div>
  </div>
</div>
<p class="cap mt16">Items only a lender can know (penal-charge amount, reset frequency, grievance officer) read "Lender to state". We never invent them. The Hindi text awaits a legal translator's review.</p>
</div>""", tag="Compliance in practice", num="10", station=7)

# ------------------------------------------------------------------ 12 decision
slide("""<div class="body">
<div class="kick">Requirement 7 of 8 · Instant decisioning</div>
<h1>Clear cases are decided alone. A person sees only what the law or the risk requires.</h1>
<div class="bar mt32"><div style="width:53.8%;background:#CFEBD9;color:#075B2D">APPROVE 53.8%</div><div style="width:8.7%;background:#F6D3D5;color:#8A0F15">8.7%</div><div style="width:37.5%;background:#FFE3B8;color:#7A3A00">REFER 37.5%</div></div>
<p class="cap mt8">1,000 synthetic applicants through the live engine, median 10 ms of compute. Green is approve, red is reject (8.7%), amber is refer.</p>
<div class="cols c2 mt32" style="gap:56px">
  <div><h3>Where the humans come in</h3>
  <table class="mt16"><thead><tr><th>Queue</th><th class="n">Share of cases</th></tr></thead><tbody>
    <tr><td>Credit (grey zone, over-ask, bureau band)</td><td class="n">25.5%</td></tr><tr><td>Fraud and compliance</td><td class="n">5.1%</td></tr><tr><td>Property (title, plan, valuation)</td><td class="n">4.9%</td></tr><tr><td>Data (a source was down)</td><td class="n">2.0%</td></tr></tbody></table></div>
  <div><h3>We tried loosening the limits</h3>
  <table class="mt16"><thead><tr><th>Eligibility threshold</th><th class="n">Automatic</th><th class="n">Default of approved</th></tr></thead><tbody>
    <tr><td>0.60 (shipped)</td><td class="n">62.5%</td><td class="n ok">3.4%</td></tr><tr><td>0.50</td><td class="n">66.4%</td><td class="n">4.2%</td></tr><tr><td>0.40</td><td class="n">69.8%</td><td class="n bad">4.9%</td></tr></tbody></table>
  <p class="cap mt8">The automatic rate rises, and so do defaults in the simulation. We left the limits; a lender sets them from its own losses.</p></div>
</div>
</div>""", tag="Instant decision", num="11", station=7)

# ------------------------------------------------------------------ 13 explainability
slide("""<div class="body">
<div class="kick">Requirement 8 of 8 · Explainability and governance</div>
<h1>Every decision is explainable, traceable and audit-ready.</h1>
<div class="cols c3 mt48">
  <div class="card"><div class="num">1</div><h3 class="mt16">Explain</h3><ul class="l mt16" style="font-size:22px"><li>Reasons on every outcome, each with its evidence</li><li>SHAP drivers and a scorecard number</li><li><b>Path to Yes:</b> the smallest change that flips a no</li><li>Printable decision letter, English or Hindi</li></ul></div>
  <div class="card"><div class="num">2</div><h3 class="mt16">Trace</h3><ul class="l mt16" style="font-size:22px"><li>Hash-chained audit log; the input is stored encrypted</li><li>Replay any decision byte for byte</li><li>Tamper detection, shown live</li><li>Engine and policy version on every decision; a changed engine is flagged, not mistaken for tampering</li></ul></div>
  <div class="card y"><div class="num">3</div><h3 class="mt16">Govern</h3><ul class="l mt16" style="font-size:22px"><li>Four-eyes: an officer cannot approve a fraud case; the Credit Head can</li><li>Referrals carry an SLA timer that escalates and audits</li><li>Model card, drift monitor, fairness check per attribute</li><li>Erasure by crypto-shredding; the chain still verifies</li></ul></div>
</div>
<p class="cap mt32">Replay, tamper detection, retention and redaction are all covered by automated tests (137 backend, 26 browser including accessibility checks).</p>
</div>""", tag="Explainability and governance", num="12", station=7)

# ------------------------------------------------------------------ 14 architecture
slide("""<div class="body">
<div class="kick">Architecture</div>
<h1>One stateless engine, a durable workflow around it, and an audit log as source of truth.</h1>
<svg viewBox="0 0 1680 560" style="margin-top:14px;width:100%;height:auto;max-height:640px" font-family="Hind" aria-label="Architecture diagram">
  <defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="#121212"/></marker></defs>
  <g stroke="#121212" stroke-width="3" fill="#fff">
    <rect x="0" y="40" width="300" height="130"/><rect x="0" y="230" width="300" height="130"/><rect x="0" y="420" width="300" height="120"/>
    <rect x="380" y="40" width="360" height="500" fill="#FFC21A"/>
    <rect x="820" y="40" width="380" height="150"/><rect x="820" y="220" width="380" height="150"/><rect x="820" y="400" width="380" height="140"/>
    <rect x="1280" y="40" width="400" height="150"/><rect x="1280" y="220" width="400" height="150"/><rect x="1280" y="400" width="400" height="140"/>
  </g>
  <g font-size="26" fill="#121212" font-weight="700">
    <text x="22" y="86">React app</text><text x="22" y="276">Lender desk</text><text x="22" y="466">Applicant sources</text>
    <text x="404" y="86">FastAPI service</text><text x="844" y="86">Temporal workflow</text><text x="844" y="266">Policy + models</text><text x="844" y="446">Audit and key vault</text>
    <text x="1304" y="86">Document readers</text><text x="1304" y="266">Observability</text><text x="1304" y="446">Hosting</text>
  </g>
  <g font-size="22" fill="#121212">
    <text x="22" y="122">Apply, case, KFS, letter,</text><text x="22" y="150">simulator, governance, EN/HI</text>
    <text x="22" y="312">Queues, review, four-eyes,</text><text x="22" y="340">admin: erase, breach register</text>
    <text x="22" y="502">Form, PDF, AA file; bureau,</text><text x="22" y="530">KYC, land (simulated)</text>
    <text x="404" y="130">Eight stage functions:</text><text x="404" y="162">data, income, property,</text><text x="404" y="194">eligibility, policy, risk,</text><text x="404" y="226">fraud, compliance</text>
    <text x="404" y="290">Decision + offer + KFS</text><text x="404" y="322">Redaction for the applicant</text><text x="404" y="354">Case-key and role auth</text><text x="404" y="386">Idempotent submit, rate limits</text>
    <text x="404" y="450">Same code runs inline when</text><text x="404" y="482">Temporal is not present</text>
    <text x="844" y="122">Parallel fetch with retries</text><text x="844" y="150">Stage activities, sealed payloads</text><text x="844" y="178">Review wait with SLA timer</text>
    <text x="844" y="302">19 hashed YAML rules</text><text x="844" y="330">Monotone LightGBM, SHAP</text><text x="844" y="358">Quantile property valuation</text>
    <text x="844" y="482">SQLite WAL, hash chain</text><text x="844" y="510">AES-256-GCM per case</text>
    <text x="1304" y="122">Text parser (default)</text><text x="1304" y="150">ReBIT AA parser</text><text x="1304" y="178">Optional local model</text>
    <text x="1304" y="302">Prometheus, Grafana</text><text x="1304" y="330">Drift (PSI), SLA metrics</text><text x="1304" y="358">Operations page</text>
    <text x="1304" y="482">Docker, Caddy, CloudFront</text><text x="1304" y="510">GitHub Actions CI</text>
  </g>
  <g stroke="#121212" stroke-width="3" fill="none" marker-end="url(#ah)">
    <path d="M300 105 H380"/><path d="M300 295 H380"/><path d="M300 480 H380"/><path d="M740 115 H820"/><path d="M740 295 H820"/><path d="M740 470 H820"/><path d="M1200 115 H1280"/><path d="M1200 295 H1280"/>
  </g>
</svg>
</div>""", tag="Architecture", num="13")

# ------------------------------------------------------------------ 15 security
slide("""<div class="body">
<div class="kick">Security and privacy</div>
<h1>Built as if the data were real, because controls should not depend on fake data.</h1>
<table class="mt32" style="font-size:22px"><thead><tr><th style="width:26%">Asset</th><th>Control</th></tr></thead><tbody>
  <tr><td><b>Applicant data</b></td><td>AES-256-GCM envelope encryption, one data key per case; the audit log stores ciphertext; the workflow engine holds sealed payloads too</td></tr>
  <tr><td><b>Who can open a case</b></td><td>A per-case capability key in the link fragment, or a staff login. A link without its key is a plain "not found"</td></tr>
  <tr><td><b>What an applicant sees</b></td><td>Fraud, sanctions, STR and risk category removed (tipping-off rules); officers' notes stay internal</td></tr>
  <tr><td><b>Rights and retention</b></td><td>Withdraw consent, access, correct, erase with a 90-day clock; a retention hold defers erasure where KYC requires records; breach register with the 72-hour deadline</td></tr>
  <tr><td><b>Inputs</b></td><td>Strict schemas, errors never echo input, control and bidi characters refused, XML entities rejected, size caps, prompt-injection treated as evidence</td></tr>
  <tr><td><b>Access</b></td><td>Salted PBKDF2 (600k), lockout per visitor and account, rate limits on the real client address behind the CDN, a private admin password on the public demo</td></tr>
  <tr><td><b>Supply chain</b></td><td>bandit, pip-audit, pnpm audit and a container build in CI on every push; all clean</td></tr>
</tbody></table>
</div>""", tag="Security and privacy", num="14")

# ------------------------------------------------------------------ 16 scale
slide("""<div class="body">
<div class="kick">Scalability and operations</div>
<h1>Measured throughput, with the limits stated.</h1>
<div class="cols c2 mt32" style="gap:64px">
  <div>
    <svg viewBox="0 0 800 430" style="width:100%;height:auto" font-family="Hind" aria-label="Decisions per second">
      <g font-size="22" fill="#121212">
        <text x="0" y="28" font-weight="700" font-size="26">Decisions per second (synthetic cases)</text>
        <text x="0" y="96">Laptop, 1 worker</text><rect x="260" y="70" width="190" height="40" fill="#121212"/><text x="460" y="100" class="mono" font-family="Azeret" font-weight="600">53 to 68</text>
        <text x="0" y="166">Laptop, 2 workers</text><rect x="260" y="140" width="380" height="40" fill="#121212"/><text x="650" y="170" font-family="Azeret" font-weight="600">133</text>
        <text x="0" y="236">Laptop, 4 workers</text><rect x="260" y="210" width="530" height="40" fill="#FFC21A" stroke="#121212" stroke-width="3"/><text x="520" y="240" font-family="Azeret" font-weight="600">185</text>
        <text x="0" y="306">1 GB cloud server (t3.micro)</text><rect x="260" y="280" width="40" height="40" fill="#121212"/><text x="310" y="310" font-family="Azeret" font-weight="600">7 to 15</text>
        <text x="0" y="376" font-size="20" fill="#55554F">Zero errors, one intact hash chain, one key per case.</text>
      </g></svg>
  </div>
  <div>
    <ul class="l" style="font-size:22px">
      <li>A 120-second sustained run on the laptop completed <b>13,718 decisions with no errors</b>, using 20 KB of storage per decision.</li>
      <li>The load test found three real bugs (lost keys, startup races, private memory). All fixed and tested.</li>
      <li>Stateless stage functions; the audit log is the shared state, so more worker processes scale it almost linearly on one machine.</li>
      <li>Temporal gives retries, durable review timers and a history; Prometheus and Grafana show decisions, stage latency, retries, drift.</li>
    </ul>
    <div class="card y mt16" style="padding:20px 26px"><p style="font-size:23px"><b>Not claimed:</b> a million decisions a day. That is 11.6 a second on average; peaks, bureau latency and the database would decide it. <span class="cap" style="color:#121212">docs/scalability.md shows the arithmetic.</span></p></div>
  </div>
</div>
</div>""", tag="Scale", num="15")

# ------------------------------------------------------------------ 17 product tour
slide("""<div class="body">
<div class="kick">The product</div>
<h1>A bold, bilingual interface, in English and Hindi, night and day, designed like Indian Railways signage.</h1>
<div class="cols c2 mt32" style="gap:20px 32px">
  <div><div class="shot" style="height:236px"><img src="img/case.png" alt="Case page" style="object-position:left top"></div><p class="cap mt8"><b>Case:</b> verdict ticket, route strip and loan terms, with a private link.</p></div>
  <div><div class="shot" style="height:236px"><img src="img/desk.png" alt="Lender desk" style="object-position:left top"></div><p class="cap mt8"><b>Lender desk:</b> referred cases with queue, fraud level and the reason.</p></div>
  <div><div class="shot" style="height:236px"><img src="img/simulator.png" alt="Policy simulator" style="object-position:left top"></div><p class="cap mt8"><b>Policy simulator:</b> change a threshold, see approvals, loss and default together.</p></div>
  <div><div class="shot" style="height:236px"><img src="img/governance.png" alt="Governance real-data check" style="object-position:left top"></div><p class="cap mt8"><b>Governance:</b> the real-data check beside audit, replay and the model card.</p></div>
</div>

</div>""", tag="Prototype", num="16")

# ------------------------------------------------------------------ 18 real / simulated / not built
slide("""<div class="body">
<div class="kick">Honesty</div>
<h1>What is real, what is simulated, and what is not built.</h1>
<div class="cols c3 mt32">
  <div class="card"><span class="tag2 t-real">Real</span><ul class="l mt16" style="font-size:22px"><li>APR arithmetic (matches the RBI example)</li><li>KFS in the Annex I layout, English and Hindi</li><li>UN Security Council list screening</li><li>ReBIT Account Aggregator file parsing</li><li>Repo rate 5.50% and RESIDEX figures</li><li>Hash-chained audit and encryption</li><li>DPDP rights flow, breach register</li></ul></div>
  <div class="card"><span class="tag2 t-sim">Simulated</span><ul class="l mt16" style="font-size:22px"><li>Bureau, KYC and land-record feeds</li><li>Every applicant and bank statement</li><li>The Account Aggregator link itself</li><li>Property price levels</li><li>Default outcomes the model is tested on</li></ul></div>
  <div class="card"><span class="tag2 t-no">Not built</span><ul class="l mt16" style="font-size:22px"><li>AA consent flow and FIU signing</li><li>OFAC, EU, UK, MHA lists; PEP data</li><li>CKYCR upload, video KYC</li><li>Quarterly statements, document release</li><li>Recovery-agent rules</li><li>Postgres; India-region hosting</li></ul></div>
</div>
</div>""", tag="Honesty", num="17")

# ------------------------------------------------------------------ 19 limits & next
slide("""<div class="body">
<div class="kick">Limits and next steps</div>
<h1>What a lender must do before this makes a real decision.</h1>
<div class="cols c2 mt32" style="gap:56px">
  <div><h3>Known limits</h3>
  <ul class="l mt16" style="font-size:22px"><li><b>No Indian loan-level data</b> we could find. Our synthetic default rate is several times the real housing NPA ratio (about 0.5% for banks at March 2026, from press reports of the RBI's June 2026 report, not checked in the primary text).</li>
  <li>Policy cut-offs (FOIR, age, bureau, default) are illustrative; only the LTV caps come from the Directions.</li>
  <li>The Hindi text needs a legal translator; the demo runs in Sydney on synthetic data.</li></ul></div>
  <div><h3>What we built to close the gap</h3>
  <ul class="l y mt16" style="font-size:22px"><li><b>Bring your own data:</b> one command, <span class="mono" style="font-size:20px;white-space:nowrap">griha.byod --csv book.csv</span>, validates a lender's loan book, retrains the same monotone calibrated model, reports out-of-sample AUC, KS and calibration, and writes a separate model. The shipped model is never overwritten.</li>
  <li><b>Hindi review kit</b> and a sign-off file; the app only drops the "unreviewed" notice when a named reviewer signs.</li>
  <li>Steps to move hosting to India, and the cut-offs to be re-set with the Policy Impact Simulator.</li></ul></div>
</div>
</div>""", tag="Roadmap", num="18")

# ------------------------------------------------------------------ 20 sources
slide("""<div class="body">
<div class="kick">Sources and citations</div>
<h1>Every figure the product relies on has a source, a date and a status.</h1>
<table class="mt8 tight" style="font-size:18px"><thead><tr><th style="width:46%">Source</th><th>Used for</th><th style="width:16%">Status</th></tr></thead><tbody>
  <tr><td>RBI Housing Finance Companies Directions, 2025 (Ch. X; Annexes IV, V)</td><td>LTV caps, KFS disclosures, valuation reports, grievance route</td><td><span class="tag2 t-real">Primary text</span></td></tr>
  <tr><td>RBI Digital Lending Directions, 2025</td><td>KFS, cooling-off, grievance, data localisation</td><td><span class="tag2 t-real">Primary text</span></td></tr>
  <tr><td>RBI NBFC KYC Directions, 2025 (RBI/DOR/2025-26/361)</td><td>KYC, AML, tipping-off, retention</td><td><span class="tag2 t-real">Primary text</span></td></tr>
  <tr><td>RBI NBFC Responsible Business Conduct Directions, 2025 (…/362)</td><td>Annex I KFS, penal charges, prepayment, APR example</td><td><span class="tag2 t-real">Primary text</span></td></tr>
  <tr><td>Digital Personal Data Protection Rules, 2025 (G.S.R. 846(E), 892(E), 843(E))</td><td>Notice, safeguards, rights, breach, retention</td><td><span class="tag2 t-real">Primary text</span></td></tr>
  <tr><td>RBI policy repo rate 5.50% (MPC, Oct 2026); NHB RESIDEX Q3 FY2025-26</td><td>Pricing base rate; market context</td><td><span class="tag2 t-real">Published</span></td></tr>
  <tr><td>UN Security Council Consolidated List (10 Nov 2026)</td><td>Sanctions screening</td><td><span class="tag2 t-real">Public list</span></td></tr>
  <tr><td>ReBIT Account Aggregator DEPOSIT FI schema</td><td>Statement file format</td><td><span class="tag2 t-real">Public spec</span></td></tr>
  <tr><td>UCI German Credit (doi:10.24432/C5NC77); Taiwan card default (doi:10.24432/C55S3H), CC BY 4.0</td><td>Real-data check of the model recipe</td><td><span class="tag2 t-real">Open data</span></td></tr>
  <tr><td>RBI Financial Stability Report, June 2026 (press reports)</td><td>Sanity check on the real housing NPA ratio</td><td><span class="tag2 t-sim">Secondary</span></td></tr>
</tbody></table>
<p class="cap mt8" style="font-size:18px">Freddie Mac loan-level data was used only for a private local check; it is not part of the product and no result is published. Links: the Data sources page in the app.</p>
</div>""", tag="Sources", num="19")

# ------------------------------------------------------------------ 21 closing
SLIDES.append(f"""<section class="slide dark" style="padding:0">
<div class="rail" style="border-color:#F7F4EA"><div class="tag"><b>21</b>Try it</div></div>
<div style="position:absolute;left:120px;right:120px;top:176px;bottom:150px;display:grid;grid-template-columns:7fr 5fr;gap:72px">
  <div>
    <div class="kick" style="color:var(--yellow)">Open it and judge for yourself</div>
    <h1 style="font-size:84px">Run a case. Open the reasons. Replay the decision.</h1>
    <div class="cols mt48" style="gap:28px;grid-template-columns:1fr">
      <div class="card y" style="color:#121212"><div class="mono" style="font-size:21px;letter-spacing:.06em;text-transform:uppercase;font-weight:600">Live demo</div><div style="margin-top:8px"><a class="mono" style="font-size:30px;font-weight:600" href="{LIVE}">{LIVE.replace("https://", "")}</a></div></div>
      <div class="card" style="background:#1d1d1b;border-color:#F7F4EA;color:#F7F4EA"><div class="mono" style="font-size:21px;letter-spacing:.06em;text-transform:uppercase;font-weight:600;color:var(--yellow)">Source code, tests, docs</div><div style="margin-top:8px"><a class="mono" style="font-size:30px;font-weight:600" href="{REPO}">github.com/anshul23102/griha</a></div></div>
    </div>
  </div>
  <div style="border-left:3px solid #F7F4EA;padding-left:48px">
    <h3 style="color:var(--yellow);font-size:32px">A two-minute tour</h3>
    <ol style="margin-top:22px;list-style:none;font-size:26px;line-height:1.4">
      <li class="row" style="margin-bottom:18px"><span class="num" style="width:44px;height:44px;font-size:21px;background:var(--yellow);color:#121212">1</span><span>Run a live case on the home page and open the full case.</span></li>
      <li class="row" style="margin-bottom:18px"><span class="num" style="width:44px;height:44px;font-size:21px;background:var(--yellow);color:#121212">2</span><span>Open the Key Facts Statement and switch to Hindi.</span></li>
      <li class="row" style="margin-bottom:18px"><span class="num" style="width:44px;height:44px;font-size:21px;background:var(--yellow);color:#121212">3</span><span>Apply with the flaky-bureau test and watch the retry.</span></li>
      <li class="row" style="margin-bottom:18px"><span class="num" style="width:44px;height:44px;font-size:21px;background:var(--yellow);color:#121212">4</span><span>Sign in as officer@griha.demo (password griha-demo) and review a referral.</span></li>
      <li class="row" style="margin-bottom:18px"><span class="num" style="width:44px;height:44px;font-size:21px;background:var(--yellow);color:#121212">5</span><span>In Governance, verify the audit chain and replay a decision.</span></li>
    </ol>
    <p style="font-size:22px;color:#B8B4A6;margin-top:26px">All applicant data is synthetic. Model metrics describe a simulation. This is a prototype, not a lending product or legal advice.</p>
  </div>
</div>
<div class="stripe" style="position:absolute;left:120px;right:120px;bottom:114px;height:22px"></div>
<div class="foot" style="color:#B8B4A6;border-color:#3A3A36;bottom:36px"><span>गृह Griha · Hero Housing Fintech Challenge · Problem Statement 2</span><span class="pg" style="color:#F7F4EA">@@N@@ / @@TOTAL@@</span></div>
</section>""")

total = len(SLIDES)
body = "".join(SLIDES).replace("@@TOTAL@@", f"{total:02d}").replace("@@N@@", f"{total:02d}")
OUT.write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Griha: automated mortgage underwriting</title><style>{CSS}</style></head><body>{body}</body></html>')
print("wrote", OUT, total, "slides")
