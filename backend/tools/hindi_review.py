"""Writes docs/hindi-review.md: every Hindi sentence that carries legal weight, next to its English, with a glossary and a sign-off block, for a qualified legal
translator to check. Run from backend/:   uv run python -m tools.hindi_review      (needs node to read the privacy page's text)

It does not translate anything. It only lays the two languages side by side so that a reviewer does not have to find the text in the code.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from griha import pricing

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "hindi-review.md"

GLOSSARY = [
    # term, Hindi used, basis
    ("Data Principal", "डेटा प्रिंसिपल", "DPDP Rules 2025, Hindi gazette text (G.S.R. 846(E)): the official Hindi text transliterates the term"),
    ("Data Fiduciary", "डेटा फिड्यूसरी", "DPDP Rules 2025, Hindi gazette text"),
    ("personal data", "वैयक्तिक डेटा", "DPDP Rules 2025, Hindi gazette text"),
    ("consent / verifiable consent", "सहमति / सत्यापन योग्य सहमति", "DPDP Rules 2025, Hindi gazette text"),
    ("notice (rule 3)", "नोटिस", "DPDP Rules 2025, Hindi gazette text"),
    ("Consent Manager", "सहमति प्रबंधक", "DPDP Rules 2025, Hindi gazette text"),
    ("Data Protection Board", "डेटा संरक्षण बोर्ड", "DPDP Rules 2025, Hindi gazette text uses \"बोर्ड\" for the Board"),
    ("Key Facts Statement (KFS)", "मुख्य तथ्य विवरण (KFS)", "Our choice. No official Hindi text of the RBI Directions was available to us"),
    ("annual percentage rate (APR)", "वार्षिक प्रतिशत दर (APR)", "Our choice"),
    ("equated monthly instalment", "समान मासिक किस्त", "Our choice; common banking usage"),
    ("floating rate", "फ्लोटिंग (परिवर्ती) दर", "Our choice. An earlier draft used \"अस्थिर\" (unstable), which reads badly, so it was changed"),
    ("benchmark / repo rate", "बेंचमार्क / रेपो दर", "Our choice"),
    ("spread", "स्प्रेड", "Our choice"),
    ("penal charges", "दंडात्मक शुल्क", "Our choice. The Directions distinguish penal charges from penal interest: the reviewer must keep that distinction"),
    ("pre-closure / foreclosure", "पूर्व-समापन", "Our choice"),
    ("pre-payment", "पूर्व-भुगतान", "Our choice"),
    ("grievance redressal officer", "शिकायत निवारण अधिकारी", "Our choice"),
    ("cooling-off period", "विचार-अवधि", "Our choice"),
    ("negative amortisation", "नकारात्मक परिशोधन", "Our choice"),
    ("Lender to state", "ऋणदाता बताएगा", "Placeholder for an item only the lender can know; never filled in by us"),
]


def _privacy_pairs() -> list[tuple[str, str, str]]:
    src = (ROOT / "frontend" / "src" / "pages" / "Privacy.tsx").read_text()
    a = src.index("const C = ") + len("const C = ")
    depth, i = 0, a
    while True:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
        if depth == 0:
            break
    js = "const C = " + src[a:i] + "; console.log(JSON.stringify(C))"
    c = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    rows = []
    for k, v in c["en"].items():
        h = c["hi"].get(k)
        if isinstance(v, list):
            rows += [(f"{k}[{n}]", e, hh) for n, (e, hh) in enumerate(zip(v, h or []))]
        elif isinstance(v, str) and h:
            rows.append((k, v, h))
    return rows


def _kfs_pairs() -> list[tuple[str, str, str]]:
    k = pricing.build_kfs(2_400_000, 0.0955, 240, "HL", "P-REVIEW")
    rows = []
    for part in ("part1", "part2"):
        for e, h in zip(k["annex_i"][part], k["hi"]["annex_i"][part]):
            rows.append((f"Annex I {part} item {e['no']}", e["item"] + (": " + e["value"] if isinstance(e["value"], str) else ""),
                         h["item"] + (": " + h["value"] if isinstance(h["value"], str) else "")))
    for e, h in zip(k["other_disclosures"], k["hi"]["other_disclosures"]):
        rows.append((f"Disclosure {e['id']} ({e['basis']})", f"{e['label']}: {e['value']}", f"{h['label']}: {h['value']}"))
    return rows


def main() -> None:
    cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")                       # noqa: E731
    md = ["# Hindi text for legal review", "",
          "**Status: not reviewed.** Written for this prototype, not by a legal translator. The Directions require the Key Facts Statement in a language the borrower understands (RBC Directions 2025 para 29), so a lender must have this checked before use.", "",
          "## How to sign off",
          "1. Read the glossary, then each pair below. Correct any wording in `backend/griha/pricing_hi.py` (the Key Facts Statement) and `frontend/src/pages/Privacy.tsx` (the privacy notice). Numbers come from the engine and must not be edited here.",
          "2. Keep the legal distinctions the English makes: a penal *charge* is not penal *interest*; \"Lender to state\" means the lender must fill the item, never us.",
          "3. When done, edit `backend/griha/data/hindi_review.json`: set `reviewed` to `true` and fill `reviewer`, `qualification` and `date`. Only then does the app stop saying the Hindi is unreviewed. A bare `true` is ignored.", "",
          "A note on sources. The Hindi text of the DPDP Rules is in the Gazette PDF; its text layer uses a legacy font and extracts garbled, so the terms below were read by decoding it. Please compare against the PDF itself. No Hindi text of the RBI Directions was available to us.", "",
          "## Glossary", "", "| English | Hindi used | Basis |", "|---|---|---|"]
    md += [f"| {cell(a)} | {cell(b)} | {cell(c)} |" for a, b, c in GLOSSARY]
    md += ["", "## Key Facts Statement (Annex I) and disclosures", "", "| Item | English | Hindi |", "|---|---|---|"]
    md += [f"| {cell(a)} | {cell(b)} | {cell(c)} |" for a, b, c in _kfs_pairs()]
    md += ["", "## Privacy notice (DPDP rule 3)", "", "| Part | English | Hindi |", "|---|---|---|"]
    md += [f"| {cell(a)} | {cell(b)} | {cell(c)} |" for a, b, c in _privacy_pairs()]
    md += ["", "## Sign-off", "", "Reviewer: ________________  Qualification: ________________  Date: ____________", ""]
    OUT.write_text("\n".join(md))
    print("wrote", OUT, f"({len(md)} lines)")


if __name__ == "__main__":
    main()
