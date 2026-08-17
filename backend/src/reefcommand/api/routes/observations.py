"""Field observation intake.

Submitting a report is the demo's re-planning trigger, so this endpoint returns
the id of the plan recompute it started along with a timestamp, letting the
dashboard measure and display responsiveness.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("")
def submit_observation() -> dict[str, object]:
    """Accept a field report, structure it, and trigger re-planning."""
    raise NotImplementedError
