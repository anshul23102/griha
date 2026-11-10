"""Temporal activities: the real work, run in the worker (same process as the API). Kept apart from the workflow module so
the deterministic workflow sandbox never imports numpy, LightGBM or prometheus."""
from __future__ import annotations

from temporalio import activity
from temporalio.exceptions import ApplicationError

from . import observability
from .runtime import STATE


def _eng():
    return STATE["engine"]


@activity.defn(name="fetch_source")
async def fetch_source(p: dict) -> dict:
    """Simulated call to one external feed. The simulated outage modes make retries and give-ups real and visible."""
    attempt = activity.info().attempt
    if attempt > 1:
        observability.observe_retry("fetch_" + p["source"])
    present = {"bank": p["has_statement"], "bureau": p["has_bureau"], "kyc": p["has_kyc"], "land": True}[p["source"]]
    if not present:
        raise ApplicationError(f"{p['source']} feed unavailable", type="FeedDown")
    if p["source"] == "bureau" and p.get("outage") == "bureau_flaky" and attempt < 3:
        raise ApplicationError(f"bureau timeout on attempt {attempt}", type="Timeout")
    return {"source": p["source"], "status": "ok", "attempts": attempt}


@activity.defn(name="assemble_data")
async def assemble_data(args: list) -> dict:
    wire, fetched = args
    e = _eng()
    ctx = e.unseal(wire)
    ctx["failed_sources"] = [f["source"] for f in fetched if f["status"] != "ok"]
    ctx["fetch"] = fetched
    return e.seal(e.s_data(ctx, e.policy))


@activity.defn(name="run_stage")
async def run_stage(args: list) -> dict:
    wire, stage = args
    e = _eng()
    if stage != "decide" and activity.info().attempt > 1:
        observability.observe_retry("stage_" + stage)
    return e.seal(e.run_stage(stage, e.unseal(wire), e.policy))


@activity.defn(name="finalize")
async def finalize(wire: dict) -> dict:
    e = _eng()
    d = e.finalize(e.unseal(wire), e.policy, record=True)
    return e.seal_blob(wire["case_id"], d.model_dump(mode="json"), b"wf-decision")


@activity.defn(name="record_review")
async def record_review(wire: dict) -> dict:
    e = _eng()
    p = e.open_blob(wire, b"wf-review")
    entry = e.audit.append(p["case_id"], "HUMAN_REVIEW", {"reviewer": p["reviewer"], "role": p["role"], "action": p["action"],
                                                          "reason": p["reason"], "engine_outcome": "REFER", "queue": p["queue"]})
    observability.REVIEWS_OPEN.dec()
    STATE.setdefault("review_state", {}).pop(p["case_id"], None)
    return e.seal_blob(p["case_id"], {"reviewer": p["reviewer"], "action": p["action"], "reason": p["reason"], "hash": entry["hash"][:12], "ts": entry["ts"]}, b"wf-review-result")


@activity.defn(name="escalate")
async def escalate(p: dict) -> dict:
    entry = _eng().audit.append(p["case_id"], "SLA_ESCALATION", {"queue": p["queue"], "waited_seconds": p["waited"]})
    observability.SLA_ESCALATIONS.inc()
    STATE.setdefault("review_state", {}).setdefault(p["case_id"], {})["escalated"] = True
    return {"hash": entry["hash"][:12]}


ACTIVITIES = [fetch_source, assemble_data, run_stage, finalize, record_review, escalate]


