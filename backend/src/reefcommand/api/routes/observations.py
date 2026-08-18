"""Field observation intake.

Submitting a report is the demo's re-planning trigger, so this endpoint returns
the id of the plan recompute it started along with a timestamp, letting the
dashboard measure and display responsiveness.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from reefcommand.api import state
from reefcommand.api.schemas import ObservationAccepted
from reefcommand.domain.observation import FieldReport

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", response_model=ObservationAccepted)
def submit_observation(report: FieldReport) -> ObservationAccepted:
    """Accept a field report, structure it, and trigger re-planning."""
    try:
        plan = state.apply_observation(report)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ObservationAccepted(
        report_id=report.report_id,
        plan=plan,
        replan_latency_ms=plan.replan_latency_ms,
    )
