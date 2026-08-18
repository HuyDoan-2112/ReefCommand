"""Operational capacity endpoints.

Every response carries the simulated-data banner.
The dashboard renders it above any plan built from the scenario.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from reefcommand.api import state
from reefcommand.api.schemas import ResourceChangeResult, ScenarioView
from reefcommand.orchestration.pipeline import load_scenario

router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceChangeRequest(BaseModel):
    """Resource scenario selected for the next planning window."""

    scenario_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


@router.get("/scenario", response_model=ScenarioView)
def get_scenario() -> ScenarioView:
    """The active simulated resource scenario."""
    plan = state.current_plan()
    scenario = load_scenario(plan.scenario_id)
    return ScenarioView(scenario=scenario, banner=scenario.display_banner())


@router.patch("/scenario", response_model=ResourceChangeResult)
def update_scenario(request: ResourceChangeRequest) -> ResourceChangeResult:
    """Change capacity, for example marking a boat unavailable, and trigger re-planning."""
    try:
        plan = state.apply_resource_change(request.scenario_id, request.description)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ResourceChangeResult(
        plan=plan,
        scenario=load_scenario(plan.scenario_id),
        banner=plan.scenario_banner,
    )
