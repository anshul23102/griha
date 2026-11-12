"""Builds the compact sanctions index (griha/data/sanctions_index.json.gz) from the four public lists. Run with `python -m griha.sanctions --refresh`.

Lists (all published free of charge by their issuers):
  UN    Security Council Consolidated List        https://scsanctions.un.org/resources/xml/en/consolidated.xml
  OFAC  US Treasury Specially Designated Nationals https://www.treasury.gov/ofac/downloads/sdn.csv and alt.csv
  EU    EU Consolidated Financial Sanctions List  https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw
        (the token in that URL is the one the EU publishes for anonymous public access)
  UK    UK Sanctions List (FCDO)                  https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml

Each entry keeps only what screening needs: the list, the reference number, individual or entity, every name and alias, and the birth years. The India MHA (UAPA)
list is not included: the Ministry publishes it as web pages with no machine-readable feed. India gives the UN lists effect under UAPA section 51A, which UN covers.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import urllib.request
from pathlib import Path

from defusedxml import ElementTree as SafeET

DATA = Path(__file__).parent / "data"
INDEX = DATA / "sanctions_index.json.gz"
URLS = {
    "UN": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    "OFAC_SDN": "https://www.treasury.gov/ofac/downloads/sdn.csv",
    "OFAC_ALT": "https://www.treasury.gov/ofac/downloads/alt.csv",
    "EU": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
    "UK": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml",
}
_YEAR = re.compile(r"\b(1[89]\d\d|20[0-2]\d)\b")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _kind(x: str) -> str:
    return "individual" if str(x).lower().startswith(("ind", "p", "person")) else "entity"


def parse_un(data: bytes) -> list[list]:
    root = SafeET.fromstring(data)
    out = []
    for kind, tag in (("individual", "INDIVIDUAL"), ("entity", "ENTITY")):
        for el in root.iter(tag):
            if el.find("DATAID") is None:
                continue
            names = [" ".join((el.findtext(f"{p}_NAME") or "").strip() for p in ("FIRST", "SECOND", "THIRD", "FOURTH")).strip()]
            names += [a.findtext("ALIAS_NAME") or "" for a in el.iter(f"{tag}_ALIAS")]
            years = set()
            for d in el.iter(f"{tag}_DATE_OF_BIRTH"):
                for f in ("YEAR", "FROM_YEAR", "TO_YEAR"):
                    v = d.findtext(f)
                    if v and v.isdigit():
                        years.add(int(v))
                v = d.findtext("DATE")
                if v and v[:4].isdigit():
                    years.add(int(v[:4]))
            out.append(["UN", el.findtext("REFERENCE_NUMBER") or "", kind, [n for n in names if n.strip()], sorted(years)])
    return out


def parse_ofac(sdn: bytes, alt: bytes) -> list[list]:
    def flip(n: str) -> str:                               # OFAC writes people as "LAST, First"
        return " ".join(reversed([p.strip() for p in n.split(",", 1)])) if "," in n else n
    aliases: dict[str, list[str]] = {}
    for row in csv.reader(io.StringIO(alt.decode("latin-1"))):
        if len(row) >= 4:
            aliases.setdefault(row[0].strip(), []).append(flip(row[3].strip()))
    out = []
    for row in csv.reader(io.StringIO(sdn.decode("latin-1"))):
        if len(row) < 12:
            continue
        ent, name, typ, remarks = row[0].strip(), row[1].strip(), row[2].strip().lower(), row[11]
        if typ in ("vessel", "aircraft"):
            continue
        years = sorted({int(y) for m in re.finditer(r"DOB([^;]*)", remarks) for y in _YEAR.findall(m.group(1))})
        out.append(["OFAC", ent, "individual" if typ == "individual" else "entity", [flip(name)] + aliases.get(ent, []), years])
    return out


def parse_eu(data: bytes) -> list[list]:
    out = []
    for _, el in SafeET.iterparse(io.BytesIO(data), events=("end",)):
        if _local(el.tag) != "sanctionEntity":
            continue
        names, years, kind = [], set(), "entity"
        for ch in el:
            t = _local(ch.tag)
            if t == "subjectType":
                kind = _kind(ch.get("classificationCode", "E"))
            elif t == "nameAlias" and ch.get("wholeName", "").strip():
                names.append(ch.get("wholeName").strip())
            elif t == "birthdate" and (ch.get("year") or "").isdigit():
                years.add(int(ch.get("year")))
        out.append(["EU", el.get("euReferenceNumber", ""), kind, names, sorted(years)])
        el.clear()
    return out


def parse_uk(data: bytes) -> list[list]:
    out = []
    for _, el in SafeET.iterparse(io.BytesIO(data), events=("end",)):
        if _local(el.tag) != "Designation":
            continue
        names = []
        for n in el.iter("Name"):
            parts = [(n.findtext(f"Name{i}") or "").strip() for i in range(1, 7)]
            full = " ".join(p for p in parts if p)
            if full:
                names.append(full)
        years = {int(y) for d in el.iter("DOB") for y in _YEAR.findall(d.text or "")}
        out.append(["UK", el.findtext("UniqueID") or "", _kind(el.findtext("IndividualEntityShip") or "Entity"), names, sorted(years)])
        el.clear()
    return out


def build(parts: dict[str, bytes]) -> dict:
    entries: list[list] = []
    dates: dict[str, str] = {}
    if "UN" in parts:
        entries += parse_un(parts["UN"]); dates["UN"] = (re.search(rb'dateGenerated="([^"]+)"', parts["UN"][:600]) or [b"", b""])[1].decode()[:10]
    if "OFAC_SDN" in parts:
        entries += parse_ofac(parts["OFAC_SDN"], parts.get("OFAC_ALT", b""))
    if "EU" in parts:
        entries += parse_eu(parts["EU"]); dates["EU"] = (re.search(rb'generationDate="([^"]+)"', parts["EU"][:800]) or [b"", b""])[1].decode()[:10]
    if "UK" in parts:
        entries += parse_uk(parts["UK"]); dates["UK"] = (re.search(rb"<DateGenerated>([^<]+)</DateGenerated>", parts["UK"][:600]) or [b"", b""])[1].decode()
    counts: dict[str, int] = {}
    for e in entries:
        counts[e[0]] = counts.get(e[0], 0) + 1
    return {"built_from": URLS, "list_dates": dates, "counts": counts, "entries": entries}


def write(index: dict, path: Path = INDEX) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))


def download(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("refusing a non-https URL")
    req = urllib.request.Request(url, headers={"User-Agent": "griha-screening"})
    with urllib.request.urlopen(req, timeout=120) as r:   # nosec B310: fixed https URLs above
        return r.read()
