"""Fraud and KYC/AML layer. Deterministic forensic checks + entity graph + anomaly model, noisy-OR combined."""
from __future__ import annotations

import statistics as st
from collections import defaultdict

import networkx as nx
import numpy as np

from .income import IncomeResult, classify_credit
from .models import ApplicationInput, Txn


def balance_breaks(txns: list[Txn], tol: float = 1.0) -> int:
    """Running balance must equal previous balance + amount. Edited PDFs usually break this."""
    n = 0
    for a, b in zip(txns, txns[1:]):
        if abs((a.balance + b.amount) - b.balance) > tol:
            n += 1
    return n


def round_trip_share(txns: list[Txn], window_days: int = 4, min_amount: float = 50_000) -> float:
    credits = [t for t in txns if t.amount >= min_amount]
    debits = [t for t in txns if t.amount < 0]
    if not credits:
        return 0.0
    matched = 0.0
    total = sum(t.amount for t in txns if t.amount > 0) or 1.0
    for c in credits:
        for d in debits:
            if 0 <= (d.d - c.d).days <= window_days and 0.9 <= (-d.amount) / c.amount <= 1.02:
                matched += c.amount
                break
    return matched / total


def window_dressing_ratio(txns: list[Txn]) -> float:
    by_month: dict[tuple, float] = defaultdict(float)
    for t in txns:
        if t.amount > 0 and classify_credit(t.narration) in ("business", "salary", "other"):
            by_month[(t.d.year, t.d.month)] += t.amount
    keys = sorted(by_month)
    if len(keys) < 4:
        return 1.0
    prior = [by_month[k] for k in keys[:-1]]
    return by_month[keys[-1]] / (st.median(prior) or 1.0)


def round_amount_share(txns: list[Txn]) -> float:
    big = [t for t in txns if t.amount >= 10_000 and classify_credit(t.narration) != "salary"]
    if len(big) < 3:
        return 0.0
    return sum(1 for t in big if t.amount % 5000 == 0) / len(big)


def behaviour_vector(txns: list[Txn]) -> list[float]:
    cr = [t.amount for t in txns if t.amount > 0] or [0.0]
    db = [-t.amount for t in txns if t.amount < 0] or [0.0]
    months = max(1, len({(t.d.year, t.d.month) for t in txns}))
    return [len(cr) / months, st.fmean(cr), st.pstdev(cr) / (st.fmean(cr) or 1.0), sum(db) / (sum(cr) or 1.0),
            len(db) / months, max(cr) / (st.median(cr) or 1.0)]


class EntityGraph:
    """Applications linked through shared phone / property / address. Detects rings and synthetic identities."""

    def __init__(self):
        self.g = nx.Graph()
        self.owner: dict[str, str] = {}

    @staticmethod
    def _keys(app: ApplicationInput) -> list[str]:
        return [f"phone:{app.applicant.phone}", f"prop:{app.property.property_id}"]

    def peek(self, app: ApplicationInput) -> dict:
        shared_phone = shared_prop = False
        for k in self._keys(app):
            for other in self.g.neighbors(k) if k in self.g else []:
                if other == f"case:{app.case_id}":
                    continue
                if self.owner.get(other) != app.applicant.pan:
                    if k.startswith("phone"):
                        shared_phone = True
                    else:
                        shared_prop = True
        me = f"case:{app.case_id}"
        owners = {app.applicant.pan}
        if me in self.g:
            owners |= {self.owner[n] for n in nx.node_connected_component(self.g, me) if n.startswith("case:") and n in self.owner}
        else:
            for k in self._keys(app):
                if k in self.g:
                    owners |= {self.owner[n] for n in nx.node_connected_component(self.g, k) if n.startswith("case:") and n in self.owner}
        size = len(owners)   # distinct applicants in the cluster: the same person re-applying is not a ring
        return {"shared_phone_other_pan": shared_phone, "shared_property_other_applicant": shared_prop, "ring_size": size}

    def forget(self, case_id: str) -> None:
        me = f"case:{case_id}"
        self.owner.pop(me, None)
        if me in self.g:
            self.g.remove_node(me)

    def add(self, app: ApplicationInput) -> None:
        me = f"case:{app.case_id}"
        self.owner[me] = app.applicant.pan
        for k in self._keys(app):
            self.g.add_edge(me, k)


def score(app: ApplicationInput, inc: IncomeResult, graph_flags: dict, anomaly: dict | None, cfg: dict) -> dict:
    t = app.statement
    flags: list[dict] = []

    def flag(code, weight, text, **data):
        flags.append({"code": code, "weight": weight, "text": text, **data})

    bb = balance_breaks(t)
    if bb >= 2:
        flag("BALANCE_BREAK", 0.75, f"{bb} transactions break the running-balance arithmetic: statement may be edited", count=bb)
    rt = round_trip_share(t)
    if rt > 0.10:
        flag("ROUND_TRIP", 0.55, f"{rt:.0%} of credits are returned to the same counterparty within days (circular flow)", share=round(rt, 3))
    wd = window_dressing_ratio(t)
    if wd > 1.8:
        flag("WINDOW_DRESSING", 0.35, f"Latest month credits are {wd:.1f}x the prior median: possible balance inflation before applying", ratio=round(wd, 2))
    ra = round_amount_share(t)
    if ra > 0.5:
        flag("ROUND_AMOUNTS", 0.2, f"{ra:.0%} of large credits are round multiples of 5,000", share=round(ra, 2))
    if inc.declared_ratio and inc.declared_ratio > cfg.get("income_inflation_ratio", 1.6):
        flag("INCOME_MISMATCH", 0.35, f"Declared income is {inc.declared_ratio:.1f}x the income supported by the statement", ratio=inc.declared_ratio)
    if app.kyc and app.kyc.name_match < 0.85:
        flag("NAME_MISMATCH", 0.45, f"Applicant name matches KYC record at only {app.kyc.name_match:.0%}", match=app.kyc.name_match)
    if graph_flags.get("shared_phone_other_pan"):
        flag("SHARED_PHONE", 0.5, "Phone number is linked to a different PAN in another application")
    if graph_flags.get("shared_property_other_applicant"):
        flag("SHARED_PROPERTY", 0.5, "Same property appears in another applicant's application")
    if graph_flags.get("ring_size", 1) >= 4:
        flag("RING", 0.5, f"Application sits in a cluster of {graph_flags['ring_size']} linked applications")
    if anomaly and anomaly.get("is_anomalous"):
        flag("BEHAVIOUR_ANOMALY", 0.30, "Account behaviour is statistically unusual versus the borrower population", score=anomaly.get("score"))
    credits_total = sum(x.amount for x in t if x.amount > 0) or 1.0
    cash_share = sum(x.amount for x in t if x.amount > 0 and "CASH DEP" in x.narration.upper()) / credits_total
    if cash_share > 0.35:
        flag("HIGH_CASH_INTENSITY", 0.25, f"{cash_share:.0%} of credits are cash deposits: AML attention", share=round(cash_share, 3))
    if app.kyc and app.kyc.pep:
        flag("PEP", 0.15, "Politically exposed person: enhanced due diligence")

    for di in app.doc_issues:
        flag(di["code"], di["weight"], di["text"])

    p_clean = 1.0
    for f in flags:
        p_clean *= 1 - f["weight"]
    s = round(1 - p_clean, 4)
    level = "high" if s >= cfg.get("fraud_refer_min", 0.5) else "medium" if s >= 0.3 else "low"
    sanctions = bool(app.kyc and app.kyc.sanctions_hit)
    aml = {"sanctions_hit": sanctions, "pep": bool(app.kyc and app.kyc.pep), "sanctions_screening": (app.kyc.sanctions_detail if app.kyc else None), "cash_share": round(cash_share, 3),
           "str_recommended": bool(sanctions or (cash_share > 0.35 and s >= 0.5))}
    return {"score": s, "level": level, "flags": flags, "aml": aml,
            "metrics": {"balance_breaks": bb, "round_trip_share": round(rt, 3), "window_dressing_ratio": round(wd, 2),
                        "round_amount_share": round(ra, 2)}}


class AnomalyModel:
    def __init__(self, forest, threshold):
        self.forest, self.threshold = forest, threshold

    def check(self, txns: list[Txn]) -> dict:
        s = float(self.forest.score_samples(np.array([behaviour_vector(txns)]))[0])
        return {"score": round(s, 4), "is_anomalous": s < self.threshold}
