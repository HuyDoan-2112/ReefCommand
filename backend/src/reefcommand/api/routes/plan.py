"""Response plan endpoints.

The plan payload includes what evidence supported each decision, what uncertainty
remains, which constraints were binding, and why each action was considered
compatible. Those are part of the contract, not optional extras.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from reefcommand.api import state
from reefcommand.domain.plan import ResponsePlan
from reefcommand.orchestration.pipeline import state_for_plan
from reefcommand.orchestration.trace import (
    ExecutionTrace,
    SiteExecutionTrace,
    failed_trace_for_id,
    for_site,
)


class RecomputeRequest(BaseModel):
    """Optional inputs for a forced plan recompute."""

    scenario_id: str = state.DEFAULT_SCENARIO_ID
    site_ids: list[str] = Field(default_factory=lambda: list(state.DEFAULT_SITE_IDS))


router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/failed-traces/{trace_id}", response_model=ExecutionTrace)
def failed_execution_trace(trace_id: str) -> ExecutionTrace:
    """Return a bounded failed-run trace when its id was reported with an error."""
    trace = failed_trace_for_id(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"unknown failed trace {trace_id!r}")
    return trace


@router.get("/current", response_model=ResponsePlan)
def current_plan() -> ResponsePlan:
    """The current response plan."""
    return state.current_plan()


@router.post("/recompute", response_model=ResponsePlan)
def recompute(request: RecomputeRequest | None = None) -> ResponsePlan:
    """Force a recompute. Returns the new plan and its latency."""
    request = request or RecomputeRequest()
    return state.recompute(request.scenario_id, request.site_ids)


@router.get("/{plan_id}/trace", response_model=ExecutionTrace)
def execution_trace(plan_id: str) -> ExecutionTrace:
    """Structured, redacted execution trace for one completed plan."""
    pipeline_state = state_for_plan(plan_id)
    if pipeline_state is None:
        raise HTTPException(status_code=404, detail=f"unknown plan {plan_id!r}")
    return pipeline_state.trace


@router.get("/{plan_id}/trace/{site_id}", response_model=SiteExecutionTrace)
def site_execution_trace(plan_id: str, site_id: str) -> SiteExecutionTrace:
    """Site agent decisions plus plan-wide stages for one completed plan."""
    pipeline_state = state_for_plan(plan_id)
    if pipeline_state is None:
        raise HTTPException(status_code=404, detail=f"unknown plan {plan_id!r}")
    try:
        return for_site(pipeline_state.trace, site_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}") from exc
