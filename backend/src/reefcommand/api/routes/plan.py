"""Response plan endpoints.

The plan payload includes what evidence supported each decision, what uncertainty
remains, which constraints were binding, and why each action was considered
compatible. Those are part of the contract, not optional extras.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from reefcommand.api import state


class RecomputeRequest(BaseModel):
    """Optional inputs for a forced plan recompute."""

    scenario_id: str = state.DEFAULT_SCENARIO_ID
    site_ids: list[str] = Field(default_factory=lambda: list(state.DEFAULT_SITE_IDS))


router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/current")
def current_plan() -> dict[str, object]:
    """The current response plan."""
    return state.current_plan().model_dump(mode="json")


@router.post("/recompute")
def recompute(request: RecomputeRequest | None = None) -> dict[str, object]:
    """Force a recompute. Returns the new plan and its latency."""
    request = request or RecomputeRequest()
    return state.recompute(request.scenario_id, request.site_ids).model_dump(mode="json")
