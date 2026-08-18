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
from reefcommand.orchestration.events import NewEvidence, PlanEvent, ResourceChange
from reefcommand.orchestration.pipeline import (
    load_scenario,
    remember_state,
    run,
    state_for_plan,
)
from reefcommand.orchestration.trace import TraceExecutor, TraceRecorder, TraceStage


def handle(event: PlanEvent, current: ResponsePlan) -> ResponsePlan:
    """Recompute only what the event invalidated, and return the updated plan."""
    state = state_for_plan(current.plan_id)
    if state is None:
        raise ValueError(
            "the current plan has no in-process pipeline state; recompute the plan before "
            "submitting a replan event"
        )

    if isinstance(event, NewEvidence):
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
    elif isinstance(event, ResourceChange):
        scenario = load_scenario(event.scenario_id)
        trigger = f"resource_change:{event.scenario_id}"
        trace_recorder = TraceRecorder(
            event.scenario_id,
            offline=state.offline,
            trigger=trigger,
        )
        updated = trace_recorder.record(
            TraceStage.OPTIMIZER,
            TraceExecutor.OPTIMIZER,
            lambda: _solve_resource_only(current, state.problem, scenario).model_copy(
                update={"replan_trigger": trigger}
            ),
            inputs={
                "source_plan_id": current.plan_id,
                "scenario_ref": scenario.scenario_id,
                "reused_evidence": True,
                "reused_policy_candidates": True,
            },
            serialize=lambda result: {
                "plan_id": result.plan_id,
                "assignment_refs": [
                    f"{assignment.site_id}:{assignment.action_id}"
                    for assignment in result.assignments
                ],
                "binding_constraints": result.binding_constraints,
            },
            rationale=lambda result: (
                "Only the optimizer reran because a resource change does not invalidate "
                f"the evidence or policy decisions; {len(result.assignments)} assignment(s) "
                "remain feasible."
            ),
            validation_checks=("or_tools_solution", "resource_constraints"),
        )
        execution_trace = trace_recorder.finalize(
            updated.plan_id,
            parent_plan_id=current.plan_id,
        )
        remember_state(
            updated,
            state.problem.model_copy(update={"scenario": scenario}),
            state.site_ids,
            state.observations,
            state.evidence_by_site,
            state.offline,
            execution_trace,
        )
    else:
        raise TypeError(f"unsupported plan event {type(event).__name__}")

    latency_ms = max(
        0,
        int((datetime.now(UTC) - _as_utc(event.received_at)).total_seconds() * 1000),
    )
    return updated.model_copy(update={"replan_latency_ms": latency_ms})


def is_plan_still_feasible(plan: ResponsePlan, scenario_id: str) -> bool | None:
    """Check current assignments against a scenario, or return None without state."""
    state = state_for_plan(plan.plan_id)
    if state is None:
        return None
    scenario = load_scenario(scenario_id)
    problem = state.problem.model_copy(update={"scenario": scenario})
    action_by_key = {(action.site_id, action.action_id): action for action in problem.candidates}
    selected = []
    boat_hours: dict[str, float] = {}
    team_hours: dict[str, float] = {}
    for assignment in plan.assignments:
        action = action_by_key.get((assignment.site_id, assignment.action_id))
        if action is None:
            return False
        selected.append(action)
        if action.resources.boats:
            boat = next(
                (
                    boat
                    for boat in scenario.boats
                    if boat.boat_id == assignment.boat_id and boat.available
                ),
                None,
            )
            if boat is None:
                return False
            boat_hours[boat.boat_id] = (
                boat_hours.get(boat.boat_id, 0.0) + action.resources.dive_hours
            )
        if action.resources.dive_teams:
            team = next(
                (
                    team
                    for team in scenario.dive_teams
                    if team.team_id == assignment.team_id and team.available_hours > 0
                ),
                None,
            )
            if team is None:
                return False
            team_hours[team.team_id] = (
                team_hours.get(team.team_id, 0.0) + action.resources.dive_hours
            )

    return (
        all(
            used <= min(boat.operational_hours, scenario.daylight_hours)
            for boat_id, used in boat_hours.items()
            for boat in scenario.boats
            if boat.boat_id == boat_id
        )
        and all(
            used <= min(team.available_hours, scenario.daylight_hours)
            for team_id, used in team_hours.items()
            for team in scenario.dive_teams
            if team.team_id == team_id
        )
        and sum(action.resources.shade_units for action in selected)
        <= scenario.inventory.shade_units
        and sum(action.resources.monitoring_kits for action in selected)
        <= scenario.inventory.monitoring_kits
        and sum(action.resources.sampling_kits for action in selected)
        <= scenario.inventory.sampling_kits
        and sum(action.resources.cost_usd for action in selected) <= scenario.budget_usd
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
