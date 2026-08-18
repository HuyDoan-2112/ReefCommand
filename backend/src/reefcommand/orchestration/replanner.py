"""Re-planning.

Owns two things.

1. Deciding the minimum set of stages that must re-run for a given event, so a
   resource change does not pay for four LLM investigators that would return
   identical results.
2. Measuring the time from evidence submitted to updated plan available. That
   number is reported, see docs/evaluation.md section C, so it is measured here
   rather than estimated later.
"""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.domain.plan import ResponsePlan
from reefcommand.domain.resources import ResourceScenario
from reefcommand.optimizer.solver import solve
from reefcommand.orchestration.events import PlanEvent
from reefcommand.orchestration.pipeline import (
    load_scenario,
    remember_state,
    run,
    state_for_plan,
)


def handle(event: PlanEvent, current: ResponsePlan) -> ResponsePlan:
    """Recompute only what the event invalidated, and return the updated plan."""
    state = state_for_plan(current.plan_id)
    if state is None:
        raise ValueError(
            "the current plan has no in-process pipeline state; recompute the plan before "
            "submitting a replan event"
        )

    if hasattr(event, "report"):
        from reefcommand.ingestion.field_reports import structure

        new_observation = structure(event.report)
        observations = [*state.observations, new_observation]
        updated = run(
            current.scenario_id,
            list(state.site_ids),
            observations=observations,
            replan_trigger=f"new_evidence:{event.report.report_id}",
            offline=state.offline,
        )
    else:
        scenario = load_scenario(event.scenario_id)
        updated = _solve_resource_only(current, state.problem, scenario)
        updated = updated.model_copy(
            update={"replan_trigger": f"resource_change:{event.scenario_id}"}
        )
        remember_state(
            updated,
            state.problem.model_copy(update={"scenario": scenario}),
            state.site_ids,
            state.observations,
            state.evidence_by_site,
            state.offline,
        )

    latency_ms = max(
        0,
        int((datetime.now(UTC) - _as_utc(event.received_at)).total_seconds() * 1000),
    )
    return updated.model_copy(update={"replan_latency_ms": latency_ms})


def is_plan_still_feasible(plan: ResponsePlan, scenario_id: str) -> bool:
    """Check the current plan against current capacity."""
    state = state_for_plan(plan.plan_id)
    if state is None:
        return False
    scenario = load_scenario(scenario_id)
    if plan.scenario_id != scenario_id:
        return False
    problem = state.problem.model_copy(update={"scenario": scenario})
    action_by_key = {(action.site_id, action.action_id): action for action in problem.candidates}
    selected = []
    for assignment in plan.assignments:
        action = action_by_key.get((assignment.site_id, assignment.action_id))
        if action is None:
            return False
        selected.append(action)
        if assignment.boat_id and not any(
            boat.boat_id == assignment.boat_id and boat.available for boat in scenario.boats
        ):
            return False
        if assignment.team_id and not any(
            team.team_id == assignment.team_id and team.available_hours > 0
            for team in scenario.dive_teams
        ):
            return False

    available_boats = [boat for boat in scenario.boats if boat.available]
    available_teams = [team for team in scenario.dive_teams if team.available_hours > 0]
    return (
        sum(action.resources.boats for action in selected) <= len(available_boats)
        and sum(action.resources.dive_teams for action in selected) <= len(available_teams)
        and sum(action.resources.dive_hours for action in selected)
        <= sum(boat.operational_hours for boat in available_boats)
        and sum(action.resources.dive_hours for action in selected)
        <= sum(team.available_hours for team in available_teams)
        and sum(action.resources.shade_units for action in selected)
        <= scenario.inventory.shade_units
        and sum(action.resources.monitoring_kits for action in selected)
        <= scenario.inventory.monitoring_kits
        and sum(action.resources.sampling_kits for action in selected)
        <= scenario.inventory.sampling_kits
        and sum(action.resources.cost_usd for action in selected) <= scenario.budget_usd
        and sum(action.resources.dive_hours for action in selected) <= scenario.daylight_hours
    )


def _solve_resource_only(
    current: ResponsePlan,
    problem: object,
    scenario: ResourceScenario,
) -> ResponsePlan:
    """Run only the optimizer against unchanged evidence and policy state."""
    from reefcommand.optimizer.model import AllocationProblem

    if not isinstance(problem, AllocationProblem):
        raise TypeError("resource-only replanning requires an AllocationProblem")
    return solve(problem.model_copy(update={"scenario": scenario}))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
