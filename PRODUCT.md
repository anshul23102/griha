# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: credit officers and the credit head at a housing finance company (Hero Housing Finance is the hackathon sponsor). They decide on Home Loan and Loan Against Property files, handle referred cases, and own credit policy. Secondary: the borrower applying (inferred, not confirmed: self-employed or informal-income buyers in Tier 2/3 cities, often on a phone). Also evaluated by hackathon judges from the lender and the E-Cell panel, who will judge in one sitting.

## Product Purpose
Griha decides Home Loan and LAP applications in seconds (approve, refer, reject) with reasons an auditor can replay, while keeping personal data encrypted and decisions tamper-evident. Success: a lender trusts a decision enough to act on it, can see why, and can change policy safely.

## Positioning
A deterministic, versioned, replayable decision engine. Language models only read and draft; they never decide. Every outcome carries its evidence chain, and policy changes are tested on a stored portfolio before shipping. A neighbouring product that lets an LLM decide could not truthfully claim this.

## Operating Context
Credit review at a desk with long files and many evidence types: bank statements, bureau reports, KYC, property records, policy rules. Reviews are repetitive and consequential. Officers need scanability and fast comparison; the credit head needs impact and audit views. Borrowers apply from a phone.

## Capabilities and Constraints
Backend (FastAPI) exposes: scenarios, applications, document upload (statement PDF), cases, path-to-yes, review with four-eyes rule, audit verify and replay, tamper demo, erasure, policy simulator, policy and compliance map, model card, login (officer and admin roles). A real multi-step application form is to be added with simulated bank, bureau and KYC adapters. All applicant data is synthetic and must be labelled so. No paid APIs; local Ollama is optional. Policy values marked internal are not regulation; the UI must keep the verified, secondary or internal labels honest. English and Hindi are both required. Light and dark themes required. A printable decision letter is required.

## Brand Commitments
Product name Griha (Sanskrit for home). No logo exists yet. Hero Housing's name is used only as the challenge sponsor, never as if Griha were Hero's product.

## Evidence on Hand
Synthetic scenarios, measured model metrics on synthetic data, a compliance map with verification status, an architecture diagram at docs/architecture.svg. No real customers, no real data, no testimonials: none may be invented.

## Product Principles
1. Reasons before verdicts: every outcome shows why in plain language before any score.
2. The evidence trail is the interface: any claim can be opened to the rule, number or document behind it.
3. Honest about uncertainty and origin: synthetic, internal and unverified are always visible.
4. Decide fast, audit forever: speed for the officer, permanence for the auditor.
5. Nothing decorative that is not wired to the backend.

## Accessibility & Inclusion
WCAG AA minimum, full keyboard use, visible focus, reduced-motion respected. Bilingual English and Hindi, with Devanagari typeset properly. Phone-first for the borrower flow; desk-first for the officer console. Never colour alone for status.
