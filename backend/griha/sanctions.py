"""Sanctions screening against four real, public lists: the UN Security Council Consolidated List, the US OFAC SDN list, the EU consolidated financial sanctions
list and the UK sanctions list (about 31,000 entries with their aliases). The lists are published free by their issuers; griha/sanctions_build.py turns them into
one compact index (griha/data/sanctions_index.json.gz). `python -m griha.sanctions --refresh` downloads them again and rebuilds it.

India gives the UN lists effect under UAPA section 51A and the RBI's KYC Directions require regulated entities to screen against them (paras 54 to 56). The other
three are what a lender with a foreign correspondent or a foreign-funded borrower is expected to screen against too. Not included: the India MHA (UAPA) list, which the
Ministry publishes as web pages with no machine-readable feed, and any politically-exposed-persons (PEP) data, which is licensed, not free.

Matching is deliberately conservative toward the human: a name that matches a listed name or alias closely, with at least two name parts in common, is a POSSIBLE
match, and a possible match goes to an officer (KYC Directions para 18); the applicant is never told (para 20(4)). It is not an automatic decline. A birth year that
contradicts the listing is recorded and downgrades a weaker name match to 'name only'.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from functools import lru_cache

from .sanctions_build import INDEX, URLS, build, download, write

THRESHOLD = 0.90
LIST_NAMES = {"UN": "UN Security Council Consolidated List", "OFAC": "US OFAC SDN list", "EU": "EU consolidated financial sanctions list", "UK": "UK sanctions list"}
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
    with gzip.open(INDEX, "rt", encoding="utf-8") as f:
        raw = json.load(f)
    entries, index = [], defaultdict(set)
    for i, (lst, ref, kind, names, years) in enumerate(raw["entries"]):
        keys = [(_key(norm(n)), n) for n in names if len(norm(n)) >= 1]
        entries.append({"list": lst, "ref": ref, "kind": kind, "name": names[0] if names else "", "keys": keys, "years": set(years)})
        for k, _ in keys:
            for t in set(k.split()):
                index[t].add(i)
    dates = raw.get("list_dates", {})
    return {"entries": entries, "index": index, "generated": ", ".join(f"{k} {v}" for k, v in dates.items()), "count": len(entries), "counts": raw.get("counts", {})}


def screen(name: str, dob_year: int | None = None) -> dict:
    """Return {'hit': bool, 'matches': [...]}; every match carries the list, its reference number, the matched name or alias and the score."""
    db = load()
    toks = norm(name)
    key = _key(toks)
    base = {"list_date": db["generated"], "checked": db["count"], "lists": sorted(db["counts"])}
    if len(toks) < 2 or not key:
        return {"hit": False, "matches": [], **base}
    qt = set(key.split())
    shared: dict[int, int] = defaultdict(int)
    for t in qt:
        for i in db["index"].get(t, ()):
            shared[i] += 1
    need = min(2, len(qt))                                    # a single shared common name (Mohammed, Kumar) is never enough
    out = []
    for i, n in shared.items():
        if n < need:
            continue
        e = db["entries"][i]
        best = max(((SequenceMatcher(None, key, k).ratio(), nm) for k, nm in e["keys"]), key=lambda x: x[0])
        if best[0] >= THRESHOLD:
            dob_ok = None if not (dob_year and e["years"]) else dob_year in e["years"]
            out.append({"list": e["list"], "ref": e["ref"], "name": best[1], "score": round(best[0], 3), "dob_year_consistent": dob_ok})
    out.sort(key=lambda m: (-m["score"], m["list"]))
    return {"hit": bool(out), "matches": out[:8], **base}


def refresh() -> None:
    parts = {k: download(u) for k, u in URLS.items()}
    for k, v in parts.items():
        if len(v) < 200_000:
            raise SystemExit(f"{k}: downloaded file is too small to be the list; index kept")
    idx = build(parts)
    if idx["counts"].get("UN", 0) < 500 or idx["counts"].get("OFAC", 0) < 5000:
        raise SystemExit("a list parsed to far fewer entries than expected; index kept")
    write(idx)
    load.cache_clear()
    print("index rebuilt:", idx["counts"], idx["list_dates"])


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    else:
        d = load()
        print("lists", d["counts"], "generated", d["generated"])
        for n in sys.argv[1:]:
            print(n, screen(n))
