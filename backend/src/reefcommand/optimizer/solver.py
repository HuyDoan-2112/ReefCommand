"""OR-Tools solve and deterministic baseline for the allocation problem."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from ortools.sat.python import cp_model

from reefcommand.domain.enums import ActionClass
from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.plan import Assignment, DeferredSite, ResponsePlan
from reefcommand.domain.resources import Boat, DiveTeam
from reefcommand.optimizer.model import AllocationProblem

SOLVER_TIME_LIMIT_SECONDS = 10.0
_SCALE = 1000


def _available_boats(problem: AllocationProblem) -> list[Boat]:
    return [boat for boat in problem.scenario.boats if boat.available]


def _available_teams(problem: AllocationProblem) -> list[DiveTeam]:
    return [team for team in problem.scenario.dive_teams if team.available_hours > 0]


def _capacity_used(actions: Iterable[EligibleAction]) -> dict[str, float]:
    actions = list(actions)
    return {
        "boat_count": sum(action.resources.boats for action in actions),
        "boat_hours": sum(action.resources.dive_hours for action in actions),
        "dive_team_count": sum(action.resources.dive_teams for action in actions),
        "dive_team_hours": sum(action.resources.dive_hours for action in actions),
        "shade_units": sum(action.resources.shade_units for action in actions),
        "monitoring_kits": sum(action.resources.monitoring_kits for action in actions),
        "sampling_kits": sum(action.resources.sampling_kits for action in actions),
        "budget_usd": sum(action.resources.cost_usd for action in actions),
        "daylight_hours": sum(action.resources.dive_hours for action in actions),
    }


def _capacity_limits(problem: AllocationProblem) -> dict[str, float]:
    scenario = problem.scenario
    return {
        "boat_count": float(len(_available_boats(problem))),
        "boat_hours": sum(boat.operational_hours for boat in _available_boats(problem)),
        "dive_team_count": float(len(_available_teams(problem))),
        "dive_team_hours": sum(team.available_hours for team in _available_teams(problem)),
        "shade_units": float(scenario.inventory.shade_units),
        "monitoring_kits": float(scenario.inventory.monitoring_kits),
        "sampling_kits": float(scenario.inventory.sampling_kits),
        "budget_usd": scenario.budget_usd,
        "daylight_hours": scenario.daylight_hours,
    }


def _binding_constraints(problem: AllocationProblem, selected: list[EligibleAction]) -> list[str]:
    used = _capacity_used(selected)
    limits = _capacity_limits(problem)
    return [name for name, limit in limits.items() if limit > 0 and abs(used[name] - limit) < 1e-6]


def _assign_resources(
    problem: AllocationProblem,
    selected: list[EligibleAction],
) -> dict[str, tuple[str | None, str | None]]:
    """Greedily attach concrete boat and team IDs after selection."""
    boat_hours = {boat.boat_id: boat.operational_hours for boat in _available_boats(problem)}
    team_hours = {team.team_id: team.available_hours for team in _available_teams(problem)}
    assignments: dict[str, tuple[str | None, str | None]] = {}
    for action in selected:
        boat_id: str | None = None
        team_id: str | None = None
        if action.resources.boats:
            for candidate_id, remaining in boat_hours.items():
                if remaining >= action.resources.dive_hours:
                    boat_id = candidate_id
                    boat_hours[candidate_id] -= action.resources.dive_hours
                    break
            if boat_id is None:
                raise RuntimeError(f"could not attach a boat to {action.action_id}")
        if action.resources.dive_teams:
            for candidate_id, remaining in team_hours.items():
                if remaining >= action.resources.dive_hours:
                    team_id = candidate_id
                    team_hours[candidate_id] -= action.resources.dive_hours
                    break
            if team_id is None:
                raise RuntimeError(f"could not attach a dive team to {action.action_id}")
        assignments[action.action_id] = (boat_id, team_id)
    return assignments


def _plan_from_selected(
    problem: AllocationProblem,
    selected: list[EligibleAction],
    *,
    assignment_ids: dict[str, tuple[str | None, str | None]] | None = None,
    replan_trigger: str | None = None,
) -> ResponsePlan:
    assignment_ids = assignment_ids or _assign_resources(problem, selected)
    assignments = [
        Assignment(
            site_id=action.site_id,
            site_name=problem.site_names.get(action.site_id, action.site_id),
            action_id=action.action_id,
            action_class=action.action_class,
            boat_id=assignment_ids[action.action_id][0],
            team_id=assignment_ids[action.action_id][1],
            priority=action.priority,
            estimated_hours=action.resources.dive_hours,
            estimated_cost_usd=action.resources.cost_usd,
            evidence_summary=(
                "Supporting causes: " + ", ".join(cause.value for cause in action.supporting_causes)
            ),
            remaining_uncertainty=(
                "Support scores are not probabilities; manager approval remains required."
            ),
            compatibility_rationale=action.provenance,
            requires_manager_approval=action.requires_manager_approval,
        )
        for action in selected
    ]
    selected_sites = {action.site_id for action in selected}
    candidate_sites = {action.site_id for action in problem.candidates}
    binding = _binding_constraints(problem, selected)
    deferred = [
        DeferredSite(
            site_id=site_id,
            site_name=problem.site_names.get(site_id, site_id),
            fallback_action_id=next(
                (
                    action.action_id
                    for action in problem.candidates
                    if action.site_id == site_id and action.action_class is ActionClass.MONITORING
                ),
                None,
            ),
            reason=(
                "Intervention deferred because " + ", ".join(binding)
                if binding
                else "Intervention was not selected by the allocation objective."
            ),
        )
        for site_id in sorted(candidate_sites - selected_sites)
    ]
    total_value = sum(
        problem.scores[action.site_id].strategic_value * action.expected_compatibility
        for action in selected
    )
    return ResponsePlan(
        plan_id=f"plan-{problem.scenario.scenario_id}",
        generated_at=datetime.now(UTC),
        scenario_id=problem.scenario.scenario_id,
        scenario_banner=problem.scenario.display_banner(),
        assignments=assignments,
        deferred=deferred,
        total_strategic_value=total_value,
        binding_constraints=binding,
        replan_trigger=replan_trigger,
    )


def solve(problem: AllocationProblem) -> ResponsePlan:
    """Maximize compatible strategic value subject to typed capacities."""
    model = cp_model.CpModel()
    candidates = problem.candidates
    selected = [model.NewBoolVar(f"select_{index}") for index in range(len(candidates))]
    boats = _available_boats(problem)
    teams = _available_teams(problem)

    boat_assignment: dict[tuple[int, int], cp_model.IntVar] = {}
    team_assignment: dict[tuple[int, int], cp_model.IntVar] = {}
    for index, action in enumerate(candidates):
        if action.resources.boats == 1:
            variables = []
            for boat_index, _boat in enumerate(boats):
                variable = model.NewBoolVar(f"candidate_{index}_boat_{boat_index}")
                boat_assignment[index, boat_index] = variable
                variables.append(variable)
            model.Add(sum(variables) == selected[index])
        if action.resources.dive_teams == 1:
            variables = []
            for team_index, _team in enumerate(teams):
                variable = model.NewBoolVar(f"candidate_{index}_team_{team_index}")
                team_assignment[index, team_index] = variable
                variables.append(variable)
            model.Add(sum(variables) == selected[index])

    by_site: dict[str, list[int]] = {}
    for index, action in enumerate(candidates):
        by_site.setdefault(action.site_id, []).append(index)
    for indexes in by_site.values():
        model.Add(sum(selected[index] for index in indexes) <= 1)

    model.Add(
        sum(selected[index] * action.resources.boats for index, action in enumerate(candidates))
        <= len(boats)
    )
    team_count_used = sum(
        selected[index] * action.resources.dive_teams for index, action in enumerate(candidates)
    )
    model.Add(team_count_used <= len(teams))
    model.Add(
        sum(
            selected[index] * int(action.resources.shade_units)
            for index, action in enumerate(candidates)
        )
        <= problem.scenario.inventory.shade_units
    )
    model.Add(
        sum(
            selected[index] * int(action.resources.monitoring_kits)
            for index, action in enumerate(candidates)
        )
        <= problem.scenario.inventory.monitoring_kits
    )
    model.Add(
        sum(
            selected[index] * int(action.resources.sampling_kits)
            for index, action in enumerate(candidates)
        )
        <= problem.scenario.inventory.sampling_kits
    )
    model.Add(
        sum(
            selected[index] * int(action.resources.dive_hours * _SCALE)
            for index, action in enumerate(candidates)
        )
        <= int(problem.scenario.daylight_hours * _SCALE)
    )
    model.Add(
        sum(
            selected[index] * int(action.resources.cost_usd * _SCALE)
            for index, action in enumerate(candidates)
        )
        <= int(problem.scenario.budget_usd * _SCALE)
    )
    for boat_index, boat in enumerate(boats):
        model.Add(
            sum(
                boat_assignment[index, boat_index] * int(action.resources.dive_hours * _SCALE)
                for index, action in enumerate(candidates)
                if (index, boat_index) in boat_assignment
            )
            <= int(boat.operational_hours * _SCALE)
        )
    for team_index, team in enumerate(teams):
        model.Add(
            sum(
                team_assignment[index, team_index] * int(action.resources.dive_hours * _SCALE)
                for index, action in enumerate(candidates)
                if (index, team_index) in team_assignment
            )
            <= int(team.available_hours * _SCALE)
        )

    objective_terms = []
    for index, action in enumerate(candidates):
        score = problem.scores[action.site_id].strategic_value
        objective_value = int(score * action.expected_compatibility * _SCALE)
        objective_terms.append(selected[index] * objective_value)
    model.Maximize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"allocation solver failed with status {solver.StatusName(status)}")

    chosen = [index for index, variable in enumerate(selected) if solver.Value(variable)]
    selected_actions = [candidates[index] for index in chosen]
    assignment_ids: dict[str, tuple[str | None, str | None]] = {}
    for index in chosen:
        action = candidates[index]
        boat_id = (
            next(
                (
                    boats[boat_index].boat_id
                    for boat_index in range(len(boats))
                    if solver.Value(boat_assignment[index, boat_index])
                ),
                None,
            )
            if action.resources.boats == 1
            else None
        )
        team_id = (
            next(
                (
                    teams[team_index].team_id
                    for team_index in range(len(teams))
                    if solver.Value(team_assignment[index, team_index])
                ),
                None,
            )
            if action.resources.dive_teams == 1
            else None
        )
        assignment_ids[action.action_id] = (boat_id, team_id)
    return _plan_from_selected(problem, selected_actions, assignment_ids=assignment_ids)


def _fits(
    problem: AllocationProblem,
    selected: list[EligibleAction],
    candidate: EligibleAction,
) -> bool:
    if any(action.site_id == candidate.site_id for action in selected):
        return False
    used = _capacity_used([*selected, candidate])
    limits = _capacity_limits(problem)
    return all(used[name] <= limit + 1e-6 for name, limit in limits.items())


def solve_baseline(problem: AllocationProblem) -> ResponsePlan:
    """Choose feasible candidates in input order as a first-reported baseline."""
    selected: list[EligibleAction] = []
    for candidate in problem.candidates:
        if _fits(problem, selected, candidate):
            selected.append(candidate)
    return _plan_from_selected(problem, selected)
