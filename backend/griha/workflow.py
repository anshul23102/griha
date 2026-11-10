"""Durable underwriting on Temporal.

UnderwritingWorkflow: four parallel source fetches (each retried, with a timeout), then each pipeline stage as its own
activity, then the decision. Its `progress` query is what the UI polls to show REAL stage progress.
ReviewWorkflow: a referred case waits for the officer's decision as a durable Update, with an SLA timer and escalation.
Workflow code is deterministic: all real work happens in activities, referenced by name so the sandbox imports nothing heavy."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

TASK_QUEUE = "griha"
SOURCES = ["bank", "bureau", "kyc", "land"]


_RETRY = RetryPolicy(initial_interval=timedelta(milliseconds=250), backoff_coefficient=2.0, maximum_attempts=3)
_ONCE = RetryPolicy(maximum_attempts=2, initial_interval=timedelta(milliseconds=100))
_T = timedelta(seconds=30)


# ------------------------------ workflows ------------------------------
@workflow.defn(name="UnderwritingWorkflow")
class UnderwritingWorkflow:
    def __init__(self) -> None:
        self._stages: list = []
        self._sources: list = []
        self._state = "running"

    @workflow.query
    def progress(self) -> dict:
        return {"state": self._state, "stages": self._stages, "sources": self._sources}

    @workflow.run
    async def run(self, wire: dict) -> dict:
        base = dict(wire["flags"])          # plain flags only: the rest of the case travels sealed

        async def fetch(src: str) -> dict:
            try:
                return await workflow.execute_activity("fetch_source", {**base, "source": src}, start_to_close_timeout=timedelta(seconds=10),
                                                       retry_policy=_RETRY)
            except ActivityError:
                return {"source": src, "status": "failed", "attempts": _RETRY.maximum_attempts}

        self._sources = [{"source": s, "status": "pending"} for s in SOURCES]
        fetched = await asyncio.gather(*[fetch(s) for s in SOURCES])
        self._sources = list(fetched)
        wire = await workflow.execute_activity("assemble_data", [wire, list(fetched)], start_to_close_timeout=_T, retry_policy=_ONCE)
        self._stages = wire["public"]
        if not wire.get("missing"):
            for stage in ["income", "property", "fraud", "eligibility", "policy", "risk", "decide"]:
                wire = await workflow.execute_activity("run_stage", [wire, stage], start_to_close_timeout=_T, retry_policy=_ONCE)
                self._stages = wire["public"]
        decision = await workflow.execute_activity("finalize", wire, start_to_close_timeout=_T, retry_policy=_ONCE)
        self._state = "done"
        return decision


@workflow.defn(name="ReviewWorkflow")
class ReviewWorkflow:
    def __init__(self) -> None:
        self._review: dict | None = None
        self._escalated = False

    @workflow.query
    def status(self) -> dict:
        return {"reviewed": self._review is not None, "escalated": self._escalated}

    @workflow.update(name="review")
    async def review(self, p: dict) -> dict:
        if self._review is not None:
            raise ApplicationError("This case was already reviewed", type="AlreadyReviewed", non_retryable=True)
        r = await workflow.execute_activity("record_review", p, start_to_close_timeout=_T, retry_policy=_ONCE)
        self._review = r
        return r

    @workflow.run
    async def run(self, p: dict) -> dict:
        try:
            await workflow.wait_condition(lambda: self._review is not None, timeout=timedelta(seconds=p["sla_seconds"]))
        except asyncio.TimeoutError:
            await workflow.execute_activity("escalate", {"case_id": p["case_id"], "queue": p["queue"], "waited": p["sla_seconds"]},
                                            start_to_close_timeout=_T, retry_policy=_ONCE)
            self._escalated = True
            await workflow.wait_condition(lambda: self._review is not None)
        return {"review": self._review, "escalated": self._escalated}


WORKFLOWS = [UnderwritingWorkflow, ReviewWorkflow]
