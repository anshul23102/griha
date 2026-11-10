"""Sanctions screening against the UN Security Council Consolidated List (real, public, machine-readable).

Source: https://scsanctions.un.org/resources/xml/en/consolidated.xml  (the UN publishes it for use by Member States and obliged entities).
India gives the UNSC lists effect through the UAPA (section 51A) and the RBI's KYC Directions require regulated entities to screen against them
(NBFC KYC Directions 2025 paras 54 to 56). A snapshot is stored at griha/data/un_consolidated.xml; `python -m griha.sanctions --refresh` replaces it.

What this is not: the OFAC, EU, UK or MHA lists, or a licensed screening vendor. It is the one list that is both legally relevant in India and free.

Matching is deliberately conservative toward the human: a name that matches a listed name or alias closely is a POSSIBLE match, and a possible match goes to
an officer (KYC Directions para 18; the applicant is never told, para 20(4)). It is not an automatic decline. A date-of-birth year that contradicts the
listing is recorded and downgrades the match to 'name only', which still goes to the officer when the name is a close full-name match.
"""
from __future__ import annotations

import re
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from defusedxml import ElementTree as SafeET

SNAPSHOT = Path(__file__).parent / "data" / "un_consolidated.xml"
URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
THRESHOLD = 0.90
_NON = re.compile(r"[^a-z0-9 ]+")
_STOP = {"bin", "ibn", "al", "el", "bint", "abu", "the", "of", "and", "mr", "mrs", "ms", "shri", "smt", "dr", "md", "mohd"}


def norm(name: str) -> list[str]:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return [t for t in _NON.sub(" ", s).split() if t]


def _key(tokens: list[str]) -> str:
    return " ".join(sorted(t for t in tokens if t not in _STOP) or sorted(tokens))


@lru_cache(maxsize=1)
def load() -> dict:
    root = SafeET.parse(str(SNAPSHOT)).getroot()
    entries, index = [], defaultdict(set)
    for kind, tag in (("individual", "INDIVIDUAL"), ("entity", "ENTITY")):
        for el in root.iter(tag):
            if el.find("DATAID") is None:
                continue
            names = [" ".join((el.findtext(f"{p}_NAME") or "").strip() for p in ("FIRST", "SECOND", "THIRD", "FOURTH")).strip()]
            names += [a.findtext("ALIAS_NAME") or "" for a in el.iter(f"{tag}_ALIAS")]
            names = [n for n in names if n.strip()]
            years: set[int] = set()
            for d in el.iter(f"{tag}_DATE_OF_BIRTH"):
                for f in ("YEAR", "FROM_YEAR", "TO_YEAR"):
                    v = d.findtext(f)
                    if v and v.isdigit():
                        years.add(int(v))
                v = d.findtext("DATE")
                if v and v[:4].isdigit():
                    years.add(int(v[:4]))
            e = {"ref": el.findtext("REFERENCE_NUMBER") or "", "list": el.findtext("UN_LIST_TYPE") or "", "kind": kind,
                 "name": names[0] if names else "", "keys": [(_key(norm(n)), n) for n in names], "years": years}
            i = len(entries)
            entries.append(e)
            for k, _ in e["keys"]:
                for t in k.split():
                    index[t].add(i)
    return {"entries": entries, "index": index, "generated": root.get("dateGenerated", ""), "count": len(entries)}


def screen(name: str, dob_year: int | None = None) -> dict:
    """Return {'hit': bool, 'matches': [...]}; every match carries the list reference, the matched name or alias and the score."""
    db = load()
    toks = norm(name)
    key = _key(toks)
    if len(toks) < 2 or not key:
        return {"hit": False, "matches": [], "list_date": db["generated"], "checked": len(db["entries"])}
    cand = set().union(*(db["index"].get(t, set()) for t in key.split())) if key else set()
    out = []
    for i in cand:
        e = db["entries"][i]
        best = max(((SequenceMatcher(None, key, k).ratio(), n) for k, n in e["keys"]), key=lambda x: x[0])
        if best[0] >= THRESHOLD:
            dob_ok = None if not (dob_year and e["years"]) else dob_year in e["years"]
            out.append({"ref": e["ref"], "list": e["list"], "name": best[1], "score": round(best[0], 3), "dob_year_consistent": dob_ok})
    out.sort(key=lambda m: -m["score"])
    return {"hit": bool(out), "matches": out[:5], "list_date": db["generated"], "checked": len(db["entries"])}


def refresh() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "griha-screening"})
    if not URL.startswith("https://"):
        raise SystemExit("refusing a non-https URL")
    with urllib.request.urlopen(req, timeout=60) as r:   # nosec B310: fixed https URL checked above
        data = r.read()
    if len(data) < 500_000 or b"CONSOLIDATED_LIST" not in data[:400]:
        raise SystemExit("downloaded file does not look like the UN consolidated list; snapshot kept")
    SNAPSHOT.write_bytes(data)
    load.cache_clear()
    print("snapshot replaced:", load()["generated"], load()["count"], "entries")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    else:
        d = load()
        print("list generated", d["generated"], "entries", d["count"])
        for n in sys.argv[1:]:
            print(n, screen(n))
