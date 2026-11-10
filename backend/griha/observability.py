"""Metrics for the whole system. Prometheus exposition at /api/metrics, plus an exact rolling window for the Operations page.
Metrics are only recorded for real (recorded) decisions, never for simulator or benchmark replays."""
from __future__ import annotations

import time
from collections import Counter as PyCounter, defaultdict, deque

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

REG = CollectorRegistry()
DECISIONS = Counter("griha_decisions_total", "Decisions by outcome", ["outcome", "queue", "product"], registry=REG)
STAGE = Histogram("griha_stage_seconds", "Engine stage latency", ["stage"], registry=REG,
                  buckets=(.0005, .001, .0025, .005, .01, .025, .05, .1, .25, .5, 1))
FRAUD_FLAGS = Counter("griha_fraud_flags_total", "Fraud flags raised", ["code"], registry=REG)
RULE_HITS = Counter("griha_policy_rule_hits_total", "Policy rules that referred or rejected", ["rule", "outcome"], registry=REG)
RISK_SCORE = Histogram("griha_risk_score", "Risk scorecard value", registry=REG, buckets=(450, 500, 550, 600, 650, 700, 750, 800))
ACT_RETRIES = Counter("griha_activity_retries_total", "Workflow activity attempts beyond the first", ["activity"], registry=REG)
WORKFLOWS = Counter("griha_workflows_total", "Underwriting runs by orchestrator and result", ["orchestrator", "result"], registry=REG)
REVIEWS_OPEN = Gauge("griha_reviews_open", "Referred cases waiting for an officer", registry=REG)
FEATURE_PSI = Gauge("griha_feature_psi", "Population stability index of live risk inputs vs reference", ["feature"], registry=REG)
SLA_ESCALATIONS = Counter("griha_sla_escalations_total", "Reviews that passed their SLA", registry=REG)
LLM_CALLS = Counter("griha_llm_calls_total", "Document-reader model calls", ["provider", "status"], registry=REG)
LLM_SECONDS = Histogram("griha_llm_seconds", "Document-reader model latency", ["provider"], registry=REG, buckets=(.5, 1, 2.5, 5, 10, 30, 60, 120))
HTTP = Histogram("griha_http_seconds", "API latency", ["route", "method", "status"], registry=REG,
                 buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10))

_stage_ms: dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
_total_ms: deque = deque(maxlen=500)
_times: deque = deque(maxlen=2000)
_flags: PyCounter = PyCounter()
_rules: PyCounter = PyCounter()
_outcomes: PyCounter = PyCounter()
_queues: PyCounter = PyCounter()
_llm: PyCounter = PyCounter()
_retries: PyCounter = PyCounter()
_started = time.time()


def observe_decision(d, product: str = "HL") -> None:
    DECISIONS.labels(d.outcome, d.refer_queue or "none", product).inc()
    _outcomes[d.outcome] += 1
    if d.refer_queue:
        _queues[d.refer_queue] += 1
    tot = 0.0
    for e in d.evidence:
        STAGE.labels(e.stage).observe(e.ms / 1000)
        _stage_ms[e.stage].append(e.ms)
        tot += e.ms
    _total_ms.append(tot)
    _times.append(time.time())
    if d.fraud:
        for f in d.fraud["flags"]:
            FRAUD_FLAGS.labels(f["code"]).inc()
            _flags[f["code"]] += 1
    for e in d.evidence:
        if e.stage == "policy":
            for r in e.data.get("rules", []):
                if r["outcome"] != "pass":
                    RULE_HITS.labels(r["id"], r["outcome"]).inc()
                    _rules[(r["id"], r["outcome"])] += 1
    if d.pd:
        RISK_SCORE.observe(d.pd["score"])


def observe_retry(activity: str) -> None:
    ACT_RETRIES.labels(activity).inc()
    _retries[activity] += 1


def observe_llm(provider: str, status: str, seconds: float) -> None:
    LLM_CALLS.labels(provider, status).inc()
    LLM_SECONDS.labels(provider).observe(seconds)
    _llm[(provider, status)] += 1


def _pct(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * q))], 2) if xs else None


def snapshot() -> dict:
    now = time.time()
    last_min = sum(1 for t in _times if now - t <= 60)
    return {
        "uptime_s": int(now - _started), "decisions": sum(_outcomes.values()), "per_minute": last_min,
        "outcomes": dict(_outcomes), "queues": dict(_queues),
        "latency_ms": {"p50": _pct(_total_ms, .5), "p95": _pct(_total_ms, .95), "n": len(_total_ms)},
        "stages": {k: {"p50": _pct(v, .5), "p95": _pct(v, .95)} for k, v in _stage_ms.items()},
        "fraud_flags": [{"code": k, "count": v} for k, v in _flags.most_common(8)],
        "rules": [{"rule": k[0], "outcome": k[1], "count": v} for k, v in _rules.most_common(8)],
        "activity_retries": dict(_retries), "llm": [{"provider": k[0], "status": k[1], "count": v} for k, v in _llm.items()],
        "reviews_open": REVIEWS_OPEN._value.get(), "sla_escalations": int(SLA_ESCALATIONS._value.get()),
    }


def exposition() -> bytes:
    return generate_latest(REG)
