"""Who is really calling. Behind a reverse proxy (and a CDN) the connecting address is the proxy's, so rate limits and login lockouts keyed on it would treat
every visitor as one person. X-Forwarded-For carries the real address, but anyone can send that header, so it is trusted only on the part of the chain that our own
infrastructure wrote.

Where the chain comes from. Our reverse proxy (Caddy 2.6) overwrites X-Forwarded-For with the peer it talks to, which behind CloudFront is the edge, so
the proxy is configured to write X-Client-Chain = "<X-Forwarded-For it received>, <its peer>". The proxy SETS that header, so a client cannot supply it. The app
prefers X-Client-Chain and falls back to X-Forwarded-For (local development).

Rule: if the connection does not come from a private or loopback address (our own reverse proxy) the header is ignored. If it does, the chain is read from the
right and the first address that is neither private nor a CloudFront edge (AWS's published ranges, griha/data/cloudfront_ranges.json) is the visitor: CloudFront
appends the viewer's address, so a value a client forged on the left is never reached.
"""
from __future__ import annotations

import ipaddress
import json
from functools import lru_cache
from pathlib import Path

RANGES_FILE = Path(__file__).parent / "data" / "cloudfront_ranges.json"


@lru_cache(maxsize=1)
def _edges() -> tuple:
    try:
        d = json.loads(RANGES_FILE.read_text())
        return tuple(ipaddress.ip_network(n) for n in d.get("ipv4", []) + d.get("ipv6", []))
    except (OSError, ValueError):
        return ()


def _is_infrastructure(a) -> bool:
    return a.is_private or a.is_loopback or a.is_link_local or any(a in n for n in _edges() if n.version == a.version)


def client_ip(peer: str | None, forwarded_for: str | None) -> str:
    try:
        p = ipaddress.ip_address(peer or "")
    except ValueError:
        return peer or "?"                                   # not an IP (a test client): use it as it is
    if not (p.is_private or p.is_loopback):
        return str(p)                                        # a direct connection: the header is attacker-controlled
    for part in reversed([x.strip() for x in (forwarded_for or "").split(",") if x.strip()]):
        try:
            a = ipaddress.ip_address(part)
        except ValueError:
            continue
        if not _is_infrastructure(a):
            return str(a)
    return str(p)
