"""Orchestrator: runs every stage, assembles an explainable APPROVE / REJECT / REFER decision, writes the audit trail.

Design rule: LLMs may extract and draft upstream, but this module is deterministic. The same input + policy hash +
model version always yields the same decision digest (see replay())."""
from __future__ import annotations

import hashlib
import time
from typing import Any

import joblib

from . import adapters, compliance, config, features, fraud, income, observability, pricing
import json

from .audit import AuditLog, canonical
from .crypto import ErasedError, Vault
from .models import ApplicationInput, Decision, Reason, StageEvidence
from .policy import Policy


class _Timer:
    def __init__(self, evidence: list[StageEvidence]):
        self.evidence = evidence

    def stage(self, name: str, fn, summarise):
        t0 = time.perf_counter()
        out = fn()
        status, summary, data = summarise(out)
        self.evidence.append(StageEvidence(stage=name, status=status, summary=summary, data=data,
                                           ms=round((time.perf_counter() - t0) * 1000, 2)))
        return out


def digest(decision: Decision) -> str:
    d = decision.model_dump(mode="json")
    for e in d["evidence"]:
        e["ms"] = 0.0
    return hashlib.sha256(canonical(d).encode()).hexdigest()


class Engine:
    def __init__(self, policy: Policy | None = None, audit: AuditLog | None = None, graph: fraud.EntityGraph | None = None,
                 vault: Vault | None = None):
        art = joblib.load(config.ARTIFACTS / "models.joblib")
        self.risk, self.valuer, self.anomaly, self.metrics = art["risk"], art["valuer"], art["anomaly"], art["metrics"]
        self.policy = policy or Policy.load(config.POLICY_PATH)
        self.audit = audit if audit is not None else AuditLog(None)
        self.graph = graph if graph is not None else fraud.EntityGraph()
        # file-backed audit log => file-backed keys; in-memory log => throwaway keys
        self.vault = vault or (Vault.from_env(config.DATA_DIR) if self.audit.path else Vault.ephemeral())

    # ---------- eligibility sizing ----------
    def _max_eligible(self, pol: Policy, app: ApplicationInput, income_est: float, obligations: float,
                      assessed: float, tenure_months: int) -> tuple[float, float]:
        best, best_cap = 0.0, 0.0
        p = pol.params
        for band in pol.data["ltv_caps"][app.loan.product]:
            cap_amount = min(p["max_loan"], band["up_to"] or p["max_loan"])
            cand = pricing.max_eligible_loan(income=income_est, obligations=obligations, tenure_months=tenure_months,
                                             foir_cap=p["foir_cap"], ltv_cap=band["cap"], assessed_value=assessed,
                                             product_max=cap_amount)
            if cand > best:
                best, best_cap = cand, band["cap"]
        return best, best_cap

    # ---------- staged pipeline ----------
    # ctx is a plain dict. Each stage reads it, appends one evidence record and returns it. The in-process path and the
    # Temporal workflow both run these exact functions; to_wire() makes a ctx JSON-safe to travel between activities.
    STAGES = ["income", "property", "fraud", "eligibility", "policy", "risk", "decide"]

    def new_ctx(self, app: ApplicationInput, pol: Policy, ov: dict | None = None, graph_flags: dict | None = None) -> dict:
        ov = ov or {}
        return {"app": app, "ov": ov, "policy_hash": pol.hash(), "gflags_in": graph_flags, "evidence": [],
                "loan_amt": float(ov.get("loan_amount", app.loan.amount)), "tenure": int(ov.get("tenure_months", app.loan.tenure_months)),
                "co": float(ov.get("co_applicant_monthly_income", app.loan.co_applicant_monthly_income))}

    @staticmethod
    def to_wire(ctx: dict) -> dict:
        out = {k: v for k, v in ctx.items() if not k.startswith("_")}
        if isinstance(out["app"], ApplicationInput):
            out["app"] = out["app"].model_dump(mode="json")
        if isinstance(out.get("inc"), income.IncomeResult):
            out["inc"] = out["inc"].model_dump()
        if isinstance(out.get("decision"), Decision):
            out["decision"] = out["decision"].model_dump(mode="json")
        return out

    def seal(self, ctx: dict) -> dict:
        """What Temporal is allowed to see: ids, flags and stage names. Everything else is AES-GCM sealed under the case key,
        so the workflow history holds no personal data and goes dark when the key is destroyed."""
        wire = self.to_wire(ctx)
        app = wire["app"]
        cid = app["case_id"]
        return {"case_id": cid, "sealed": self.vault.encrypt(cid, canonical(wire).encode(), b"wf-ctx"), "missing": wire.get("missing", []),
                "flags": {"has_statement": bool(app["statement"]), "has_bureau": app["bureau"] is not None, "has_kyc": app["kyc"] is not None,
                          "outage": app.get("outage", "none")},
                "public": [{"stage": e["stage"], "status": e["status"], "ms": e["ms"]} for e in wire["evidence"]]}

    def unseal(self, w: dict) -> dict:
        return json.loads(self.vault.decrypt(w["case_id"], w["sealed"], b"wf-ctx"))

    def seal_blob(self, case_id: str, obj: dict, aad: bytes) -> dict:
        return {"case_id": case_id, "sealed": self.vault.encrypt(case_id, canonical(obj).encode(), aad)}

    def open_blob(self, w: dict, aad: bytes) -> dict:
        return json.loads(self.vault.decrypt(w["case_id"], w["sealed"], aad))

    @staticmethod
    def _app(ctx: dict) -> ApplicationInput:
        if not isinstance(ctx["app"], ApplicationInput):
            ctx["app"] = ApplicationInput.model_validate(ctx["app"])
        return ctx["app"]

    @staticmethod
    def _inc(ctx: dict) -> income.IncomeResult:
        if not isinstance(ctx["inc"], income.IncomeResult):
            ctx["inc"] = income.IncomeResult(**ctx["inc"])
        return ctx["inc"]

    @staticmethod
    def _ev(ctx: dict, name: str, status: str, summary: str, data: dict, t0: float) -> None:
        ctx["evidence"].append({"stage": name, "status": status, "summary": summary, "data": data,
                                "ms": round((time.perf_counter() - t0) * 1000, 2)})

    def run_stage(self, name: str, ctx: dict, pol: Policy | None = None) -> dict:
        return getattr(self, "s_" + name)(ctx, pol or self.policy)

    def s_data(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        app = self._app(ctx)
        failed = set(ctx.get("failed_sources", []))
        missing = [n for n, v in (("bureau", app.bureau), ("kyc", app.kyc), ("bank_statement", app.statement)) if not v]
        missing += [n for n, key in (("bureau", "bureau"), ("kyc", "kyc"), ("bank_statement", "bank")) if key in failed and n not in missing]
        srcs = adapters.sources(app, failed, ctx.get("fetch"))
        docs = adapters.documents(app, fraud.balance_breaks(app.statement))
        ctx["missing"] = missing
        self._ev(ctx, "data_integration", "fail" if missing else "warn" if any(x["status"] in ("warning", "failed") for x in docs) else "ok",
                 f"Missing sources: {', '.join(missing)}" if missing else f"{sum(x['status'] == 'ok' for x in srcs)} of {len(srcs)} sources fetched, {sum(x['status'] == 'verified' for x in docs)} of {len(docs)} documents verified",
                 {"sources": srcs, "documents": docs, "statement_source": app.statement_source}, t0)
        return ctx

    def s_income(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        app = self._app(ctx)
        inc = income.analyse(app.statement, app.applicant.employment, app.applicant.declared_monthly_income, app.bureau.active_obligations_monthly)
        ctx["inc"] = inc
        self._ev(ctx, "income", "ok" if inc.confidence != "low" else "warn",
                 f"Assessed income {inc.est_monthly_income:,.0f}/month over {inc.observed_months} months ({inc.confidence} confidence)", inc.model_dump(), t0)
        return ctx

    @staticmethod
    def _independent_needed(amount: float, pol: Policy) -> int:
        """Independent valuation reports required for a loan of this size (RBI HFC Directions Annex V): from the first threshold two
        reports with at least one independent (our own model estimate counts as the other), from the second two independent reports."""
        p = pol.params
        return 2 if amount >= p["valuation_two_independent_from"] else 1 if amount >= p["valuation_two_reports_from"] else 0

    def s_property(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        p = self._app(ctx).property
        r = self.valuer.assess(p)
        # RBI HFC Directions Annex V paras 1.5 and 1.6: where several valuation reports exist, the lower one decides the loan amount.
        r["valuation_reports"] = {"model": r["assessed_value"], "independent": [round(x) for x in p.independent_valuations]}
        if p.independent_valuations:
            r["assessed_value"] = min(r["assessed_value"], round(min(p.independent_valuations)))
        r["valuation_reports"]["used"] = r["assessed_value"]
        ctx["prop"] = r
        extra = f"; lower of {1 + len(p.independent_valuations)} valuation reports used" if p.independent_valuations else ""
        self._ev(ctx, "property", "warn" if r["flags"] else "ok", f"Assessed value {r['assessed_value']:,} (model range {r['p10']:,} to {r['p90']:,}){extra}", r, t0)
        return ctx

    def s_fraud(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        app = self._app(ctx)
        gflags = ctx["gflags_in"] if ctx.get("gflags_in") is not None else self.graph.peek(app)
        ctx["gflags"] = gflags
        r = fraud.score(app, self._inc(ctx), gflags, self.anomaly.check(app.statement), pol.params)
        ctx["fr"] = r
        self._ev(ctx, "fraud", "fail" if r["level"] == "high" else "warn" if r["level"] == "medium" else "ok",
                 f"Fraud score {r['score']:.2f} ({r['level']}), {len(r['flags'])} flag(s)", {**r, "graph": gflags}, t0)
        return ctx

    def s_eligibility(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        app, inc = self._app(ctx), self._inc(ctx)
        est = features.effective_income(app, inc, ctx["co"])
        max_loan, cap = self._max_eligible(pol, app, est, features.obligations(app, inc), float(ctx["prop"]["assessed_value"]), ctx["tenure"])
        ctx.update(est_income=est, max_loan=max_loan, cap_used=cap, offered=min(ctx["loan_amt"], max_loan))
        self._ev(ctx, "eligibility", "ok", f"Supportable loan {pricing.inr_short(max_loan)} (FOIR cap {pol.params['foir_cap']:.0%}, LTV cap {cap:.0%})",
                 {"max_eligible_loan": max_loan, "ltv_cap_used": cap, "foir_cap": pol.params["foir_cap"], "stress_rate": config.UW_RATE}, t0)
        return ctx

    def s_policy(self, ctx: dict, pol: Policy) -> dict:
        t0 = time.perf_counter()
        app, inc = self._app(ctx), self._inc(ctx)
        loan_amt, tenure = ctx["loan_amt"], ctx["tenure"]
        age = features.age_years(app)
        req = features.build(app, inc, float(ctx["prop"]["assessed_value"]), loan_amt, tenure, ctx["co"])
        metrics: dict[str, Any] = {
            "pan_verified": app.kyc.pan_verified, "aadhaar_verified": app.kyc.aadhaar_verified, "sanctions_hit": app.kyc.sanctions_hit,
            "age": age, "age_at_maturity": age + tenure / 12,
            "bureau_score": app.bureau.score, "dpd_max_12m": app.bureau.dpd_max_12m, "writeoff": app.bureau.writeoff,
            "est_income": ctx["est_income"], "observed_months": inc.observed_months, "loan_amount": loan_amt,
            "tenure_years": tenure / 12, "tenure_cap_years": pol.tenure_cap_years(app.loan.product),
            "max_eligible_loan": ctx["max_loan"], "eligibility_ratio": (ctx["max_loan"] / loan_amt) if loan_amt else 0.0,
            "undisclosed_obligations": inc.statement_obligations > 1.25 * app.bureau.active_obligations_monthly + 1000,
            "title_blocked": ctx["prop"]["title_blocked"], "encumbrance": app.property.encumbrance, "approved_plan": app.property.approved_plan,
            "foir_requested": req["foir"], "ltv_requested": req["ltv"],
            "valuation_shortfall": max(0, self._independent_needed(ctx["offered"], pol) - len(app.property.independent_valuations))}
        r = pol.evaluate(metrics)
        ctx["rules"] = r
        self._ev(ctx, "policy", "fail" if any(x["outcome"] == "reject" for x in r) else "warn" if any(x["outcome"] == "refer" for x in r) else "ok",
                 f"{sum(x['outcome'] == 'pass' for x in r)}/{len(r)} rules passed (policy {pol.version}, {pol.hash()})",
                 {"rules": r, "metrics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in metrics.items()}}, t0)
        return ctx

    def s_risk(self, ctx: dict, pol: Policy) -> dict:
        ctx["risk"] = None
        if ctx["offered"] >= pol.params["min_loan"]:
            t0 = time.perf_counter()
            feats = features.build(self._app(ctx), self._inc(ctx), float(ctx["prop"]["assessed_value"]), ctx["offered"], ctx["tenure"], ctx["co"])
            r = self.risk.predict(feats)
            ctx["risk"] = r
            self._ev(ctx, "risk", "ok", f"PD {r['pd']:.1%} (80% band {r['pd_lo']:.1%} to {r['pd_hi']:.1%})",
                     {**r, "features": {k: (None if v != v else round(v, 4)) for k, v in feats.items()}}, t0)
        return ctx

    def s_decide(self, ctx: dict, pol: Policy) -> dict:
        app, fr, prop, risk = self._app(ctx), ctx["fr"], ctx["prop"], ctx["risk"]
        results, offered, loan_amt, tenure = ctx["rules"], ctx["offered"], ctx["loan_amt"], ctx["tenure"]
        rejects = [r for r in results if r["outcome"] == "reject"]
        refers = [r for r in results if r["outcome"] == "refer"]
        reasons: list[Reason] = [Reason(code=r["id"], kind="policy", text=r["reason"]) for r in rejects + refers]
        reasons += [Reason(code=f["code"], kind="fraud", text=f["text"], weight=f["weight"]) for f in fr["flags"]]
        reasons += [Reason(code=f["code"], kind="property", direction="info", text=f["text"]) for f in prop["flags"]]
        P = pol.params
        outcome, queue, headline, offer, kfs = None, None, "", None, None
        if rejects:
            outcome, headline = "REJECT", "Declined: " + rejects[0]["reason"]
        elif fr["level"] == "high":
            outcome, queue, headline = "REFER", "FRAUD", "Referred to fraud review: " + fr["flags"][0]["text"]
        elif refers:
            outcome, headline = "REFER", "Referred to credit officer: " + refers[0]["reason"]
            ids = [r["id"] for r in refers]
            queue = ("FRAUD" if any(i.startswith("AML") for i in ids) else "DATA" if any(i.startswith("KYC") for i in ids)
                     else "PROPERTY" if refers[0]["id"].startswith(("TITLE", "APPROVED", "VALUATION")) else "CREDIT")
            if queue == "FRAUD":
                headline = "Referred to the compliance officer: " + next(r["reason"] for r in refers if r["id"].startswith("AML"))
        elif risk is None:
            outcome, headline = "REJECT", "Declined: no supportable loan amount"
        elif risk["pd_lo"] >= P["pd_reject_min"]:
            outcome, headline = "REJECT", f"Declined: predicted default risk {risk['pd']:.0%} is above the acceptable limit"
        elif risk["pd"] <= P["pd_approve_max"] and risk["pd_hi"] <= P["pd_approve_max"] * P["pd_uncertainty_factor"]:
            outcome = "APPROVE"
        else:
            outcome, queue, headline = "REFER", "CREDIT", f"Referred to credit officer: risk {risk['pd']:.1%} is in the grey zone or the model is uncertain"
        if outcome == "APPROVE":
            rate = pricing.offer_rate(risk["pd"], app.loan.product)
            offer = {"amount": offered, "requested": loan_amt, "reduced": offered < loan_amt, "tenure_months": tenure, "rate_pct": round(rate * 100, 2),
                     "emi": round(pricing.emi(offered, rate, tenure))}
            kfs = pricing.build_kfs(offered, rate, tenure, app.loan.product, proposal_no="P-" + app.case_id)
            headline = (f"Approved: {pricing.inr_short(offered)} at {rate * 100:.2f}% for {tenure // 12} years" +
                        (f" (reduced from {pricing.inr_short(loan_amt)} to fit income)" if offered < loan_amt else ""))
        if risk:
            for dvr in [d for d in risk["drivers"] if d["direction"] == ("favourable" if outcome == "APPROVE" else "adverse")][:3]:
                reasons.append(Reason(code=f"RISK_{dvr['feature'].upper()}", kind="risk", direction=dvr["direction"], text=f"{dvr['label']}: {dvr['value']}", weight=dvr["log_odds"]))
        t0 = time.perf_counter()
        assessed = float(prop["assessed_value"])
        ltv_off = (offered / assessed) if (assessed > 0 and offered > 0) else None
        c = compliance.evaluate(app, outcome=outcome, refer_queue=queue, offer=offer, kfs=kfs, reasons=reasons, ltv_offered=ltv_off, ltv_cap=ctx["cap_used"] or None,
                                vault_on=self.vault is not None, fraud_level=fr["level"], str_recommended=fr["aml"]["str_recommended"])
        self._ev(ctx, "compliance", "ok", f"{sum(x['status'] == 'met' for x in c)} met, {sum(x['status'] == 'enforced' for x in c)} enforced, {sum(x['status'] == 'na' for x in c)} not applicable", {"controls": c}, t0)
        ctx["decision"] = Decision(case_id=app.case_id, policy_version=pol.version, policy_hash=pol.hash(), model_version=self.risk.version,
                                   outcome=outcome, refer_queue=queue, headline=headline, reasons=reasons, offer=offer, kfs=kfs, pd=risk, fraud=fr,
                                   evidence=[StageEvidence(**e) for e in ctx["evidence"]])
        return ctx

    def finalize(self, ctx: dict, pol: Policy | None = None, record: bool = True) -> Decision:
        pol = pol or self.policy
        app = self._app(ctx)
        if ctx.get("missing"):
            d = Decision(case_id=app.case_id, policy_version=pol.version, policy_hash=pol.hash(), model_version=self.risk.version, outcome="REFER", refer_queue="DATA",
                         headline="Referred: required data is missing",
                         reasons=[Reason(code="DATA_MISSING", kind="data", text=f"Could not obtain: {', '.join(ctx['missing'])}")],
                         evidence=[StageEvidence(**e) for e in ctx["evidence"]])
            gflags: dict = {}
        else:
            d = ctx["decision"]
            if not isinstance(d, Decision):
                d = Decision.model_validate(d)
            gflags = ctx.get("gflags", {})
        return self._finish(app, d, ctx["ov"], gflags, record)

    # ---------- main entry (in process) ----------
    def underwrite(self, app: ApplicationInput, *, policy: Policy | None = None, overrides: dict | None = None,
                   graph_flags: dict | None = None, record: bool = True) -> Decision:
        pol = policy or self.policy
        ctx = self.new_ctx(app, pol, overrides, graph_flags)
        self.s_data(ctx, pol)
        if not ctx["missing"]:
            for name in self.STAGES:
                self.run_stage(name, ctx, pol)
        return self.finalize(ctx, pol, record)

    def _finish(self, app, d: Decision, ov: dict, gflags: dict, record: bool) -> Decision:
        if record:
            if not self.audit.for_case_event(app.case_id, "DECISION"):    # idempotent: a retried activity must not write twice
                enc = self.vault.encrypt(app.case_id, canonical(app.model_dump(mode="json")).encode(), b"audit-input")
                self.audit.append(app.case_id, "DECISION", {"input_enc": enc, "overrides": ov, "graph_flags": gflags,
                                                           "outcome": d.outcome, "digest": digest(d), "policy_hash": d.policy_hash, "engine_version": config.ENGINE_VERSION,
                                                           "model_version": d.model_version})
                self.graph.add(app)
                observability.observe_decision(d, app.loan.product)
        return d

    def replay(self, entry: dict) -> dict:
        """Re-run a recorded decision from its stored inputs and compare digests."""
        p = entry["payload"]
        try:
            raw = json.loads(self.vault.decrypt(entry["case_id"], p["input_enc"], b"audit-input")) if "input_enc" in p else p["input"]
        except ErasedError:
            return {"erased": True, "match": None, "recorded_outcome": p["outcome"], "replayed_outcome": None,
                    "policy_hash_match": None, "model_match": None}
        app = ApplicationInput.model_validate(raw)
        d = self.underwrite(app, overrides=p["overrides"], graph_flags=p["graph_flags"], record=False)
        rec_engine = p.get("engine_version", "1.0.0")           # entries written before versioning were made by 1.0.0
        return {"match": digest(d) == p["digest"], "engine_recorded": rec_engine, "engine_current": config.ENGINE_VERSION, "engine_match": rec_engine == config.ENGINE_VERSION,
                "recorded_outcome": p["outcome"], "replayed_outcome": d.outcome,
                "policy_hash_match": d.policy_hash == p["policy_hash"], "model_match": d.model_version == p["model_version"]}
