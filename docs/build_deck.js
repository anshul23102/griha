const P = require('/opt/homebrew/lib/node_modules/pptxgenjs');
const p = new P(); p.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
const D = __dirname + '/';
const INK='121212', Y='FFC21A', BL='12439A', G='4A4F57';
const F='Helvetica Neue';
function base(title, kicker){
  const s = p.addSlide(); s.background={color:'FFFFFF'};
  s.addShape(p.ShapeType.rect,{x:0,y:0,w:13.33,h:0.9,fill:{color:Y}});
  s.addShape(p.ShapeType.rect,{x:0,y:0.9,w:13.33,h:0.07,fill:{color:INK}});
  s.addText(title,{x:0.5,y:0.1,w:12.3,h:0.7,fontFace:F,fontSize:26,bold:true,color:INK,valign:'middle',margin:0});
  if(kicker) s.addText(kicker,{x:0.5,y:1.1,w:12.3,h:0.5,fontFace:F,fontSize:15,color:G,margin:0});
  s.addText('Griha · every applicant shown is synthetic',{x:0.5,y:7.1,w:8,h:0.3,fontFace:F,fontSize:10,color:G,margin:0});
  return s;
}
function pic(s,f,w,h,x,y,maxw,maxh){ const r=Math.min(maxw/w,maxh/h); s.addImage({path:D+f,x,y,w:w*r,h:h*r}); }
function bullets(s,items,x,y,w,fs=17){
  s.addText(items.map(t=>({text:t,options:{bullet:{indent:16},breakLine:true,paraSpaceAfter:9}})),{x,y,w,h:5,fontFace:F,fontSize:fs,color:INK,valign:'top',margin:0});
}
// 1 title
let s=p.addSlide(); s.background={color:INK};
s.addShape(p.ShapeType.rect,{x:0,y:5.9,w:13.33,h:0.25,fill:{color:Y}});
s.addText('गृह · Griha',{x:0.7,y:1.3,w:12,h:1,fontFace:F,fontSize:54,bold:true,color:Y,margin:0});
s.addText('Automated mortgage underwriting that explains itself',{x:0.7,y:2.4,w:12,h:0.8,fontFace:F,fontSize:30,color:'FFFFFF',margin:0});
s.addText('Home Loan + LAP · humanless where safe, referred where not · replayable, auditable, regulator-aware',{x:0.7,y:3.4,w:12,h:0.6,fontFace:F,fontSize:17,color:'C9CED6',margin:0});
s.addText('Hero Housing Fintech Challenge · Problem Statement 2 · i-Hack, IIT Bombay E-Summit 2026',{x:0.7,y:6.4,w:12,h:0.4,fontFace:F,fontSize:14,color:'C9CED6',margin:0});
// 2 approach
s=base('The decision is deterministic. The models only help.','Models read and draft; a versioned, hashed, replayable engine decides.');
bullets(s,['Eight PS2 requirements covered end to end: data, eligibility, fraud + KYC/AML, risk, documents + property, compliance, instant decision, explainability.','Policy as code: 18 YAML rules, hashed, traced on every case. Change a threshold in the simulator and replay stored cases first, with a fairness check.','Risk: monotone boosted trees, isotonic calibration, conformal sets, SHAP reasons, 650-point scorecard.','Every decision comes with plain-language reasons and a Path to Yes when it is fixable.','Hindi and English, light and dark, printable decision letter.'],0.5,1.8,12.3);
// 3 live demo
s=base('One click runs the real engine','Home page: pick a scenario, get a verdict with reasons in about 20 ms of compute.');
pic(s,'img/home.png',2040,1290,0.5,1.7,12.3,5.3);
// 4 case
s=base('A case is a ticket you can read and replay','Verdict, reason, queue, terms, then the route it travelled and the Temporal history behind it.');
pic(s,'img/case.png',2040,1290,0.5,1.7,12.3,5.3);
// 5 architecture
s=base('Architecture','Temporal runs the stages as retried activities; Prometheus and Grafana watch them.');
pic(s,'architecture.png',2000,1300,0.9,1.65,11.5,5.4);
// 6 controls + sources
s=base('Compliance and data lineage on every case','15 controls per decision; each data source shows attempts, status and consent.');
pic(s,'img/controls.png',1812,2046,0.5,1.65,4.6,5.35);
pic(s,'img/sources.png',1806,1208,5.4,1.9,7.4,4.9);
// 7 ops
s=base('Operations: live numbers, not a mock-up','In-app Operations page reads the same Prometheus registry that Grafana scrapes.');
pic(s,'img/ops.png',2040,1290,0.4,1.7,6.2,4.6); pic(s,'img/grafana.png',2040,1290,6.8,1.7,6.2,4.6);
s.addText('Decisions, stage latency, retries, fraud flags, rule hits, review backlog, SLA escalations.',{x:0.5,y:6.45,w:12.3,h:0.4,fontFace:F,fontSize:14,color:G,margin:0});
// 8 temporal
s=base('Durable by construction','Kill the API mid-case and the workflow resumes; a flaky bureau is retried three times and shown as attempt 3.');
pic(s,'img/temporal.png',2040,1290,0.5,1.7,8.2,5.3);
bullets(s,['UnderwritingWorkflow: parallel fetches, one activity per stage.','ReviewWorkflow: officer decision is a Temporal Update; an SLA timer escalates and audits.','Workflow history holds only AES-GCM sealed payloads. Destroy the case key and the history is unreadable.'],8.95,1.9,3.9,15);
// regulation
s=base('Compliance built from the primary text','RBI Housing Finance Companies Directions 2025, read in the source PDF, not from summaries.');
pic(s,'img/kfs.png',2040,1290,0.4,1.7,6.3,4.0); pic(s,'img/mitc.png',2040,1290,6.8,1.7,6.2,4.0);
bullets(s,['Key Fact Statement carries the para 131 disclosures: all-in cost, refunds, penal and conversion charges, reset, 60-day exit. Lender-set values are marked.','Printable terms sheet in the Annex IV layout; loans of Rs 50 lakh and up need the valuation reports Annex V requires, or go to the property team.'],0.5,5.85,12.3,13);
// data sources
s=base('Where every number comes from','Published figures, synthetic data and our own assumptions are kept apart, each with a link and a date.');
pic(s,'img/datasources.png',2040,1290,0.5,1.65,7.3,4.6);
bullets(s,['Real: RBI repo rate 5.50% (October 2026 minutes) drives the base and stress rates; NHB RESIDEX shows each city\'s price trend.','Rejected sources are listed too, with the reason.','Real-loan validation: planned, pending clearance from the data owner.'],8.1,1.8,4.8,14);
// business impact
s=base('Business impact, with the assumptions on the table','Measured on 400 synthetic cases through the live engine; time and cost are inputs you can change.');
pic(s,'img/impact.png',1812,944,0.5,1.65,8.2,4.3);
bullets(s,['Measured: 61% of cases decided by the engine alone; median 11 ms of compute.','Assumed (editable): 45 officer minutes per manual file, 20 per referred file, Rs 500 an hour.','Nothing here comes from a real lender.'],9.0,1.8,3.9,14);
// scalability
s=base('Scalability, measured and bounded','docs/scalability.md: real load test, real bugs found and fixed.');
s.addTable([
  [{text:'Machine',options:{bold:true}},{text:'Workers',options:{bold:true}},{text:'Decisions per second',options:{bold:true}},{text:'p95 latency',options:{bold:true}},{text:'Errors',options:{bold:true}}],
  ['Laptop, 8 cores','1','53 to 68','16 to 300 ms','0'],['Laptop','2','133','93 ms','0'],['Laptop','4','185','64 ms','0'],
  ['Free-tier server, 1 GB','1','7 to 15','190 ms to 1.1 s','0'],['Free-tier server','2','out of memory','','errors']],
  {x:0.5,y:1.7,w:12.3,fontFace:F,fontSize:14,color:INK,border:{type:'solid',color:'C9CED6',pt:1},rowH:0.42});
bullets(s,['Adding processes scales it; one transactional SQLite store keeps one hash chain and one key per case.','The load test exposed three multi-worker bugs (lost case keys, startup races, private case memory). All fixed and tested.','Limits: synthetic cases, short bursts, one machine. Several machines need Postgres, which is not built.'],0.5,4.9,12.3,14);
// security
s=base('Built for confidential data','Every control below has a test.');
bullets(s,['Encrypted at rest and inside the workflow engine: AES-256-GCM, one key per case. Erase a case by destroying its key.','A case belongs to its creator: a 128-bit private link, or a staff login. Anyone else gets a plain not-found.','Salted PBKDF2 (600k rounds), account lockout, revocable sessions, four-eyes approval on fraud referrals.','Input hardening, strict CSP and security headers, restart-safe audit chain, no known vulnerable dependencies.','Honest limits: master key in a file (KMS in production), demo users, no TLS termination in the app.'],0.5,1.8,12.3,17);
// 9 honesty
s=base('What is real, and what is not','Stated up front so nobody has to find it.');
bullets(s,['Real: engine, workflows, encryption, audit chain, observability, typed document agent (tested on a local model), 94 backend tests, 18 browser tests including accessibility.','Synthetic: all applicants and training data. Bureau, Account Aggregator, KYC and land-record feeds are simulated adapters with the same interfaces a live integration needs.','Illustrative: policy thresholds and lender-set charges, except what is read from the RBI HFC Directions 2025 (LTV caps, Fair Practices Code, valuation rule). The NBFC Responsible Business Conduct Directions, which hold the KFS format, were not read.','Real-loan validation is planned and awaits the data owner\'s clearance; nothing from it is claimed.','Honest model finding: a logistic baseline (AUC 0.760) is indistinguishable from the boosted model (0.747) on synthetic data. We ship the monotone, explainable one and say why.','Hindi covers the interface and finding titles; engine sentences stay English.'],0.5,1.8,12.3,16);
// 10 close
s=base('Try it','Everything above runs locally with one command.');
bullets(s,['ops/start.sh launches Temporal, Prometheus, Grafana, the API and the web app.','Demo script: 3 minutes for the product, 90 seconds for the engineering tour.','Judging criteria map: accuracy and feasibility, use of data, explainability, regulatory fit, scalability, clarity.'],0.5,1.9,12.3,19);
p.writeFile({fileName:D+'Griha-submission.pptx'}).then(()=>console.log('ok'));
