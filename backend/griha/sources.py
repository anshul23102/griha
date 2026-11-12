"""Registry of every data source, regulation and assumption the product relies on, with its provenance and honest status.
The Data sources page and /api/sources read this; nothing here is invented: each real figure carries a link, a publication date
and the date we retrieved it. Status words: verified (read at the primary source), secondary (reported by a secondary source),
internal (our own illustrative assumption), synthetic (generated), pending (identified, not yet obtained)."""
from __future__ import annotations

from . import config

RETRIEVED = "2026-11-10"

RESIDEX = {
    "title": "NHB RESIDEX, Q3 FY2025-26 (Oct to Dec 2025), HPI at Assessment Prices, base FY2017-18",
    "published": "March 2026",
    "url": "https://www.nhb.org.in/wp-content/uploads/2026/03/National-Press-Release-RESIDEX-Dec25-DV002.pdf",
    "composite_yoy_pct": 5.0, "composite_qoq_pct": 1.8, "composite_yoy_year_ago_pct": 7.2,
    "range_yoy_pct": {"high": ["Gurugram", 22.8], "low": ["Raipur", -8.9]},
    "cities_growing": 46, "cities_total": 50,
    "city_yoy_pct": {"Ahmedabad": 6.8, "Bengaluru": 12.7, "Chennai": 8.2, "Hyderabad": 3.2, "Kolkata": 6.7, "Mumbai": 3.7, "Pune": 3.5},
}


def market_context(city: str) -> dict:
    """Real published price trend for a city, for display next to a case. Information only: it is not an input to any decision."""
    yoy = RESIDEX["city_yoy_pct"].get(city)
    return {"city": city, "city_yoy_pct": yoy, "composite_yoy_pct": RESIDEX["composite_yoy_pct"], "quarter": "Q3 FY2025-26", "source": "NHB RESIDEX",
            "url": RESIDEX["url"], "published": RESIDEX["published"]}


def registry() -> list[dict]:
    r = RESIDEX
    return [
        {"id": "rbi-repo", "group": "real", "status": "verified", "name": "RBI policy repo rate", "publisher": "Reserve Bank of India",
         "value": f"{config.REPO_RATE * 100:.2f}%", "as_of": "7 Oct 2026 (minutes published 21 Oct 2026)", "retrieved": RETRIEVED,
         "url": "https://rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63839",
         "detail": "The MPC raised the repo rate by 25 bp to 5.50% and changed its stance to calibrated tightening (6-0 on the rate; 4-2 on the stance).",
         "used_for": f"config.REPO_RATE. Base rate = repo + {config.LENDER_SPREAD * 100:.1f}% lender spread = {config.BASE_RATE * 100:.2f}%; stress rate = base + {config.STRESS_BUFFER * 100:.1f}% = {config.UW_RATE * 100:.2f}%. A repo change moves quotes and eligibility one for one. The spread and buffer are illustrative."},
        {"id": "nhb-residex", "group": "real", "status": "verified", "name": "NHB RESIDEX housing price index", "publisher": "National Housing Bank",
         "value": f"50-city composite +{r['composite_yoy_pct']}% year on year (+{r['composite_qoq_pct']}% quarter on quarter; {r['composite_yoy_year_ago_pct']}% a year earlier)",
         "as_of": "Q3 FY2025-26, published " + r["published"], "retrieved": RETRIEVED, "url": r["url"],
         "detail": "City year-on-year change: " + ", ".join(f"{c} {v:+.1f}%" for c, v in r["city_yoy_pct"].items()) +
                   f". Range {r['range_yoy_pct']['high'][0]} +{r['range_yoy_pct']['high'][1]}% to {r['range_yoy_pct']['low'][0]} {r['range_yoy_pct']['low'][1]}%; "
                   f"{r['cities_growing']} of {r['cities_total']} cities grew.",
         "used_for": "Market context shown next to a case for its city. Information only: it is not an input to any decision, and our valuation model is trained on synthetic comparables."},
        {"id": "digital-lending", "group": "real", "status": "verified", "name": "RBI (Digital Lending) Directions, 2025", "publisher": "Reserve Bank of India",
         "value": "Applies to HFCs (para 3(iii)); KFS (8(i)); cooling-off of at least one day (10); grievance officer and RBI escalation after 30 days (11); explicit, revocable consent (12); data stored only in India (13(iv))",
         "as_of": "issued 8 May 2025", "retrieved": RETRIEVED, "url": "https://www.rbi.org.in/scripts/FS_Notification.aspx?Id=12848",
         "detail": "Paragraph numbers read in the RBI text. Para 8(i) points to the KFS format, which is now Annex I of the NBFC Responsible Business Conduct Directions 2025 (read, see that row).",
         "used_for": f"KFS and letter wording (a {config.COOLING_OFF_DAYS}-day cooling-off line, which is illustrative because the lender's Board sets it, and the RBI complaint route), the consent record, and the rule that production data must be stored in India. The hosted demo runs outside India with synthetic data only."},
        {"id": "fpc", "group": "real", "status": "verified", "name": "RBI Housing Finance Companies Directions, 2025: Chapter X Fair Practices Code and Annexes IV and V", "publisher": "Reserve Bank of India",
         "value": "Paras 129 to 177 (Fair Practices Code), Annex IV (KFS and MITC), Annex V (valuation by loan size)", "as_of": "RBI/DoR/2025-26/365, 28 Nov 2025; text version dated 21 Oct 2026", "retrieved": RETRIEVED,
         "url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12939",
         "detail": "Read in the primary PDF. Built from it: written reasons for rejection (135); all-in cost and fee, penal, conversion, reset and refund disclosures on the KFS (131, 132); 60-day exit if terms worsen (137); grievance acknowledgement, response times and the NHB Complaint Redressal Cell (142 to 144); no pre-payment charge on floating-rate housing loans (163); a terms sheet in the Annex IV layout (165); non-discrimination (168); confidentiality (160); Hindi or English (167); the valuation-reports rule (Annex V 1.5, 1.6, 1.8). Not built: signing and handover of the MITC, DSA and recovery-agent rules, notice-board display.",
         "used_for": "Compliance controls, KFS and letter wording, the terms sheet page, and the policy rule that refers loans of Rs 50 lakh or more to the property team until the required independent valuation reports are on file. The PDF is kept on the developer's machine, not redistributed; we cite paragraph numbers and paraphrase."},
        {"id": "hfc-ltv", "group": "real", "status": "verified", "name": "Loan-to-value caps for housing finance companies", "publisher": "Reserve Bank of India",
         "value": "90% up to Rs 30 lakh, 80% to Rs 75 lakh, 75% above", "as_of": "RBI HFC Directions 2025, para 58", "retrieved": "2026-11-09", "url": "https://www.rbi.org.in",
         "detail": "Read in the primary directions: para 58 and its note (the LTV numerator is the total outstanding without netting; stamp duty and registration charges are not financed, except for houses up to Rs 10 lakh).", "used_for": "policy/v1.yaml LTV bands for home loans. The LAP cap of 60% is an internal choice."},
        {"id": "rebit-aa", "group": "real", "status": "verified", "name": "ReBIT Account Aggregator FI schema, DEPOSIT type", "publisher": "ReBIT (Reserve Bank Information Technology), published for the Account Aggregator ecosystem",
         "value": "Account > Profile > Holders > Holder, Summary, Transactions > Transaction; transaction type CREDIT or DEBIT; mode CASH, ATM, CARD, UPI, FT or OTHERS", "as_of": "specification page as published; the page does not state a release number (ReBIT announced version 2.0.0 for Deposit, RD and TD on 23 Jan 2025)",
         "retrieved": RETRIEVED, "url": "https://specifications.rebit.org.in/api_schema/account_aggregator/documentation/deposit.html",
         "detail": "Element and attribute names, mandatory fields and enumerations were read on the published specification page. Built: a parser that accepts a DEPOSIT document (XML or the same names in JSON), validates the mandatory fields, and runs the same checks as a PDF statement. Not built: the consent artefact, signed FIU requests to an Account Aggregator, and decryption of the FI payload. Those need a registered FIU, which a student project cannot be.",
         "used_for": "The Account Aggregator adapter (griha/aa.py): bank data in the format an Account Aggregator returns becomes the same statement object the engine already scores. Sample documents are synthetic."},
        {"id": "rbc", "group": "real", "status": "verified", "name": "RBI (NBFC) Responsible Business Conduct Directions, 2025", "publisher": "Reserve Bank of India",
         "value": "RBI/DOR/2025-26/362, 28 Nov 2025, 37 pages; applies to HFCs (para 3(7))", "as_of": "28 Nov 2025", "retrieved": RETRIEVED,
         "url": "https://www.rbi.org.in/Scripts/BS_ViewMasterDirections.aspx",
         "detail": "Read in the primary PDF. Built from it: the standardised Key Facts Statement of Annex I (Part 1 and Part 2), with a proposal number and a validity of at least three working days (29(1), (2)); the APR computation sheet and the amortisation schedule (29(3)); no fee that is not in the KFS (29(5)); the borrower's acknowledgement kept on record (13, 29(1)); how the rate was set and graded by risk (22 to 24); penal charges as a charge, not interest, not capitalised, disclosed upfront (30); floating-rate reset options and the 25 bps impact (31, Annex I item 7); no pre-payment charge on floating-rate loans to individuals for non-business purposes (34). Our APR method reproduces the RBI's own worked example (17.07%). Not built: the Hindi KFS, the quarterly statement (31(6)), release of property documents (35 to 41), DSA and recovery-agent rules, the KFS summary box in the loan agreement (29(6)), the lender-set items (shown as Lender to state).",
         "used_for": "The KFS page (/case/<id>/kfs), the KFS and pre-payment controls, and the rate-basis disclosure."},
        {"id": "kyc-md", "group": "real", "status": "verified", "name": "RBI (NBFC) Know Your Customer Directions, 2025, updated to 29 Dec 2025", "publisher": "Reserve Bank of India",
         "value": "RBI/DOR/2025-26/361, 28 Nov 2025, 96 pages; applies to HFCs through HFC Directions para 5(23)", "as_of": "28 Nov 2025, updated 29 Dec 2025", "retrieved": RETRIEVED,
         "url": "https://www.rbi.org.in/SCRIPTs/BS_ViewMasterDirections.aspx?did=411",
         "detail": "Read in the primary PDF. Built from it: KYC before any transaction (17(3)); PAN verified with the issuing authority (17(10)); an officer records the reason for any rejection and no application is rejected without application of mind (18); the decision on KYC compliance is not outsourced (13); Aadhaar is voluntary, so another officially valid document is accepted (23, explanation 4); an online application is non-face-to-face, so the customer is rated high-risk with enhanced checks (44); PEP rules (45); the risk category and its reasons, any suspicion, and the fact of an STR stay confidential from the customer (19, 20(4), 52); identification and transaction records kept five years (47); customer data not used for cross-selling or shared without permission (61). Built: screening against the real UN Security Council Consolidated List (griha/sanctions.py, snapshot with a refresh command). Not built: OFAC, EU, UK and MHA lists, PEP data, CKYCR upload within 10 days (63), V-CIP, address positive confirmation (44(3)), periodic KYC updation (42).",
         "used_for": "The KYC, AML, EDD and STR controls; the applicant's redacted view (griha/redact.py); routing of PAN and sanctions findings to an officer instead of an automatic decline; the retention hold on erasure."},
        {"id": "dpdp", "group": "real", "status": "verified", "name": "Digital Personal Data Protection Rules, 2025 (G.S.R. 846(E)) with corrigendum G.S.R. 892(E), and commencement notification G.S.R. 843(E)", "publisher": "Ministry of Electronics and Information Technology, Gazette of India",
         "value": "Rule 3 notice (itemised data, specific purpose, how to withdraw consent, exercise rights, complain to the Board); rule 6 safeguards (encryption or masking, access control, logs, backups, one-year log retention); rule 7 breach notice and 72-hour report; rule 8(3) one-year minimum retention of data and logs; rule 9 contact; rule 14 rights and a response within 90 days",
         "as_of": "notified 13 Nov 2025; Rule 4 (consent managers) one year after publication, rules 3 and 5 to 16 eighteen months after (13 May 2027); Data Protection Board established by G.S.R. 844(E)", "retrieved": RETRIEVED,
         "url": "https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf",
         "detail": "Read in the gazette text (41 pages) and the three notifications. Built now although most rules start on 13 May 2027: the privacy notice page, consent wording, data-rights requests logged with a 90-day deadline, withdrawal of consent that stops processing, erasure that waits for any retention duty, per-case encryption, access-controlled logs, and a backup script. Not built: breach-notification workflow (rule 7), consent-manager integration (rule 4), nominee requests (14(4)), a named Data Protection Officer (the lender must name one).",
         "used_for": "The privacy notice (/privacy), the data-rights card on a case, the consent controls, and docs/security.md."},
        {"id": "india-npa", "group": "secondary", "status": "secondary", "name": "Reality check: non-performing housing loans at Indian banks", "publisher": "RBI Financial Stability Report, June 2026 (as reported in the press; the report itself was not read)",
         "value": "About 0.5% of housing loans non-performing at March 2026, down from 1.2% in March 2019; secured retail 0.7%, unsecured retail 1.7%", "as_of": "March 2026", "retrieved": RETRIEVED,
         "url": "https://www.policycircle.org/economy/rbi-financial-stability-report-loans/",
         "detail": "Secondary source: the figures come from press coverage of the June 2026 Financial Stability Report and have not been checked against the RBI text. They are portfolio-level figures for banks, not loan-level data and not for housing finance companies.",
         "used_for": "A sanity check only. The synthetic world's default rate is several times the real Indian housing NPA ratio, so the model's absolute probabilities are NOT Indian default rates and the policy cut-offs are not calibrated to the real book. A lender must retrain on its own loans (python -m griha.byod) and re-set the cut-offs. Nothing in the engine is derived from this number."},
        {"id": "freddie", "group": "pending", "status": "pending", "name": "Freddie Mac Single-Family Loan-Level Dataset", "publisher": "Freddie Mac",
         "value": "Real US mortgage origination and performance records", "as_of": "Terms effective November 2025; Release 47 user guide, July 2026", "retrieved": RETRIEVED,
         "url": "https://freddiemac.com/research/datasets/sf-loanlevel-dataset",
         "detail": "Free after registration. Licence: personal or internal use to analyse credit performance; academic or research results may be made public for non-commercial purposes if they cannot be used to recreate the data or identify anyone; the data and any Derived Products may not be given to third parties; no re-identification. Source: Freddie Mac, Terms and Conditions for the Single-Family Loan-Level Dataset.",
         "used_for": "Planned, local only: score real US loans with the existing synthetic-trained model and measure how well it ranks real defaults. The shipped model is never trained on this data, the data never enters the repository, the hosted demo or any deploy, and aggregate results will only be published after Freddie Mac confirms in writing that a student competition entry is acceptable. It is US data, so it tests the pipeline on real loans; it is not Indian calibration."},
        {"id": "icpsr-india", "group": "rejected", "status": "rejected", "name": "Loan-level mortgage data from India (openICPSR replication package)", "publisher": "openICPSR project 116500, Campbell, Ramadorai and Ranish (American Economic Association)",
         "value": "Paper describes over a million loans disbursed 1995 to 2010", "as_of": "V1, 7 Dec 2019; inspected " + RETRIEVED, "retrieved": RETRIEVED,
         "url": "https://www.openicpsr.org/openicpsr/project/116500/version/V1/view",
         "detail": "The package contains a code folder and a licence file only. The loan-level data itself is not included, so there is nothing to download.",
         "used_for": "Not used. The only real Indian loan-level source we found turned out to be code without data."},
        {"id": "kaggle-in", "group": "rejected", "status": "rejected", "name": "Indian loan datasets mirrored on Kaggle", "publisher": "Various uploaders",
         "value": "Small tables labelled as Indian home-loan or loan-default data", "as_of": "reviewed " + RETRIEVED, "retrieved": RETRIEVED, "url": "https://www.kaggle.com/datasets",
         "detail": "Several describe themselves as synthetic and the rest give no provenance or licence we could verify.",
         "used_for": "Not used. Presenting unverified data as real would be worse than saying we do not have it."},
        {"id": "synthetic-pop", "group": "synthetic", "status": "synthetic", "name": "Applicant population and bank statements", "publisher": "Generated by this project (griha/synth.py)",
         "value": "Reproducible synthetic applicants", "as_of": "seeded", "retrieved": "", "url": "",
         "detail": "Every applicant, statement and training row is generated. Cities and price tiers are Indian; no real person is represented.",
         "used_for": "Training and testing the risk and valuation models. Accuracy figures on this data show the model learned the generator, not real-world performance."},
        {"id": "adapters", "group": "synthetic", "status": "synthetic", "name": "Account Aggregator, credit bureau, KYC and land-record feeds", "publisher": "Simulated adapters (griha/adapters.py)",
         "value": "Deterministic per applicant", "as_of": "seeded", "retrieved": "", "url": "",
         "detail": "Same interface a live integration needs; no real feed is called.",
         "used_for": "Demonstrates retries, outages and lineage. Real feeds would replace the adapters."},
        {"id": "policy", "group": "internal", "status": "internal", "name": "Credit policy thresholds", "publisher": "This project (policy/v1.yaml)",
         "value": f"FOIR cap, score cut-offs, age and tenure limits, LAP LTV; lender spread {config.LENDER_SPREAD * 100:.1f}%, stress buffer {config.STRESS_BUFFER * 100:.1f}%",
         "as_of": "policy v1.1.0", "retrieved": "", "url": "",
         "detail": "Illustrative values a lender would set itself. The policy file is hashed and every decision records the hash.",
         "used_for": "Eligibility, policy rules and pricing."},
    ]
