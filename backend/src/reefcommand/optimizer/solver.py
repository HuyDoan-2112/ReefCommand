"""Deterministic OR-Tools allocation and baseline policies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from uuid import uuid4

from ortools.sat.python import cp_model

from reefcommand.domain.enums import ActionClass
from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.plan import Assignment, DeferredSite, ResponsePlan
from reefcommand.domain.resources import Boat, DiveTeam
from reefcommand.optimizer.model import AllocationProblem

SOLVER_TIME_LIMIT_SECONDS = 10.0
SOLVER_RANDOM_SEED = 20260818
_SCALE = 1000
_TIE_SCALE = 10_000
_CAPACITY_KEYS = (
    "boat_hours",
    "dive_team_hours",
    "shade_units",
    "monitoring_kits",
    "sampling_kits",
    "budget_usd",
)
_CONSTRAINT_PROSE = {
    "boat_hours": "available boat operating time",
    "dive_team_hours": "available dive-team time",
    "shade_units": "available shade units",
    "monitoring_kits": "available monitoring kits",
    "sampling_kits": "available sampling kits",
    "budget_usd": "the simulated operating budget",
}
AssignmentKey = tuple[str, str]


@dataclass(frozen=True)
class _ModelParts:
    model: cp_model.CpModel
    selected: list[cp_model.IntVar]
    boats: list[Boat]
    teams: list[DiveTeam]
    boat_assignment: dict[tuple[int, int], cp_model.IntVar]
    team_assignment: dict[tuple[int, int], cp_model.IntVar]


@dataclass(frozen=True)
class _SolveResult:
    chosen: list[int]
    objective: int
    assignments: dict[AssignmentKey, tuple[str | None, str | None]]


def _available_boats(problem: AllocationProblem) -> list[Boat]:
    return [boat for boat in problem.scenario.boats if boat.available]


def _available_teams(problem: AllocationProblem) -> list[DiveTeam]:
    return [team for team in problem.scenario.dive_teams if team.available_hours > 0]


def _primary_objective_value(problem: AllocationProblem, index: int) -> int:
    action = problem.candidates[index]
    strategic = problem.scores[action.site_id].strategic_value
    return int(strategic * action.expected_compatibility * _SCALE)


def _objective_value(problem: AllocationProblem, index: int) -> int:
    primary = _primary_objective_value(problem, index)
    return primary * _TIE_SCALE + len(problem.candidates) - index


def _build_model(
    problem: AllocationProblem,
    *,
    relaxed: frozenset[str] = frozenset(),
    forced_site_id: str | None = None,
    force_all: bool = False,
) -> _ModelParts:
    model = cp_model.CpModel()
    candidates = problem.candidates
    selected = [model.NewBoolVar(f"select_{index}") for index in range(len(candidates))]
    boats = _available_boats(problem)
    teams = _available_teams(problem)
    boat_assignment: dict[tuple[int, int], cp_model.IntVar] = {}
    team_assignment: dict[tuple[int, int], cp_model.IntVar] = {}

    for index, action in enumerate(candidates):
        if action.resources.boats not in (0, 1) or action.resources.dive_teams not in (0, 1):
            raise ValueError(
                "the prototype optimizer supports at most one boat and team per action"
            )
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
    for site_id, indexes in by_site.items():
        model.Add(sum(selected[index] for index in indexes) <= 1)
        if site_id == forced_site_id:
            model.Add(sum(selected[index] for index in indexes) == 1)
    if forced_site_id is not None and forced_site_id not in by_site:
        raise ValueError(f"cannot force unknown candidate site {forced_site_id!r}")
    if force_all:
        for variable in selected:
            model.Add(variable == 1)

    inventory_constraints = {
        "shade_units": ("shade_units", problem.scenario.inventory.shade_units),
        "monitoring_kits": ("monitoring_kits", problem.scenario.inventory.monitoring_kits),
        "sampling_kits": ("sampling_kits", problem.scenario.inventory.sampling_kits),
    }
    for key, (field, limit) in inventory_constraints.items():
        if key not in relaxed:
            model.Add(
                sum(
                    selected[index] * int(getattr(action.resources, field))
                    for index, action in enumerate(candidates)
                )
                <= limit
            )
    if "budget_usd" not in relaxed:
        model.Add(
            sum(
                selected[index] * int(action.resources.cost_usd * _SCALE)
                for index, action in enumerate(candidates)
            )
            <= int(problem.scenario.budget_usd * _SCALE)
        )

    if "boat_hours" not in relaxed:
        for boat_index, boat in enumerate(boats):
            limit = min(boat.operational_hours, problem.scenario.daylight_hours)
            model.Add(
                sum(
                    boat_assignment[index, boat_index] * int(action.resources.dive_hours * _SCALE)
                    for index, action in enumerate(candidates)
                    if (index, boat_index) in boat_assignment
                )
                <= int(limit * _SCALE)
            )
    if "dive_team_hours" not in relaxed:
        for team_index, team in enumerate(teams):
            limit = min(team.available_hours, problem.scenario.daylight_hours)
            model.Add(
                sum(
                    team_assignment[index, team_index] * int(action.resources.dive_hours * _SCALE)
                    for index, action in enumerate(candidates)
                    if (index, team_index) in team_assignment
                )
                <= int(limit * _SCALE)
            )

    model.Maximize(
        sum(selected[index] * _objective_value(problem, index) for index in range(len(candidates)))
    )
    return _ModelParts(model, selected, boats, teams, boat_assignment, team_assignment)


def _solve_model(
    problem: AllocationProblem,
    *,
    relaxed: frozenset[str] = frozenset(),
    forced_site_id: str | None = None,
    force_all: bool = False,
) -> _SolveResult | None:
    parts = _build_model(
        problem,
        relaxed=relaxed,
        forced_site_id=forced_site_id,
        force_all=force_all,
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    solver.parameters.random_seed = SOLVER_RANDOM_SEED
    solver.parameters.num_search_workers = 1
    status = solver.Solve(parts.model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    chosen = [index for index, variable in enumerate(parts.selected) if solver.Value(variable)]
    assignments: dict[AssignmentKey, tuple[str | None, str | None]] = {}
    for index in chosen:
        action = problem.candidates[index]
        boat_id = next(
            (
                parts.boats[boat_index].boat_id
                for boat_index in range(len(parts.boats))
                if (index, boat_index) in parts.boat_assignment
                and solver.Value(parts.boat_assignment[index, boat_index])
            ),
            None,
        )
        team_id = next(
            (
                parts.teams[team_index].team_id
                for team_index in range(len(parts.teams))
                if (index, team_index) in parts.team_assignment
                and solver.Value(parts.team_assignment[index, team_index])
            ),
            None,
        )
        assignments[(action.site_id, action.action_id)] = (boat_id, team_id)
    primary_objective = sum(_primary_objective_value(problem, index) for index in chosen)
    return _SolveResult(chosen, primary_objective, assignments)


def _binding_constraints(problem: AllocationProblem, base_objective: int) -> list[str]:
    """Find the smallest capacity relaxations that improve the objective."""
    for size in range(1, len(_CAPACITY_KEYS) + 1):
        improving = []
        for keys in combinations(_CAPACITY_KEYS, size):
            relaxed = _solve_model(problem, relaxed=frozenset(keys))
            if relaxed is not None and relaxed.objective > base_objective:
                improving.append(keys)
        if improving:
            involved = {key for keys in improving for key in keys}
            return [key for key in _CAPACITY_KEYS if key in involved]
    return []


def _forced_site_blockers(site_id: str, problem: AllocationProblem) -> list[str]:
    for size in range(1, len(_CAPACITY_KEYS) + 1):
        feasible = []
        for keys in combinations(_CAPACITY_KEYS, size):
            if (
                _solve_model(
                    problem,
                    relaxed=frozenset(keys),
                    forced_site_id=site_id,
                )
                is not None
            ):
                feasible.append(keys)
        if feasible:
            involved = {key for keys in feasible for key in keys}
            return [key for key in _CAPACITY_KEYS if key in involved]
    return []


def _deferral_reason(site_id: str, problem: AllocationProblem, binding: list[str]) -> str:
    forced = _solve_model(problem, forced_site_id=site_id)
    blockers = _forced_site_blockers(site_id, problem) if forced is None else binding
    if blockers:
        prose = [_CONSTRAINT_PROSE[key] for key in blockers]
        explanation = prose[0] if len(prose) == 1 else ", ".join(prose[:-1]) + f" and {prose[-1]}"
        return (
            "Deferred because selecting a response at this site would trade off against "
            f"higher-value feasible work under {explanation}."
        )
    return (
        "Deferred because another feasible combination produced greater strategic value "
        "under the current simulated capacity."
    )


def _plan_from_result(
    problem: AllocationProblem,
    result: _SolveResult,
    *,
    replan_trigger: str | None = None,
) -> ResponsePlan:
    selected = [problem.candidates[index] for index in result.chosen]
    assignments = []
    for action in selected:
        boat_id, team_id = result.assignments[(action.site_id, action.action_id)]
        assignments.append(
            Assignment(
                site_id=action.site_id,
                site_name=problem.site_names.get(action.site_id, action.site_id),
                action_id=action.action_id,
                action_class=action.action_class,
                boat_id=boat_id,
                team_id=team_id,
                priority=action.priority,
                estimated_hours=action.resources.dive_hours,
                estimated_cost_usd=action.resources.cost_usd,
                evidence_summary=(
                    "Supporting causes: "
                    + ", ".join(cause.value for cause in action.supporting_causes)
                ),
                remaining_uncertainty=(
                    "Support scores are not probabilities; manager approval remains required."
                ),
                compatibility_rationale=action.provenance,
                requires_manager_approval=action.requires_manager_approval,
            )
        )
    selected_sites = {action.site_id for action in selected}
    candidate_sites = {action.site_id for action in problem.candidates}
    binding = _binding_constraints(problem, result.objective)
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
            reason=_deferral_reason(site_id, problem, binding),
        )
        for site_id in sorted(candidate_sites - selected_sites)
    ]
    total_value = sum(
        problem.scores[action.site_id].strategic_value * action.expected_compatibility
        for action in selected
    )
    return ResponsePlan(
        plan_id=f"plan-{problem.scenario.scenario_id}-{uuid4().hex[:12]}",
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
    """Maximize compatible strategic value under deterministic typed capacities."""
    result = _solve_model(problem)
    if result is None:
        raise RuntimeError("allocation solver found no feasible plan")
    return _plan_from_result(problem, result)


def _fits(problem: AllocationProblem, actions: Iterable[EligibleAction]) -> bool:
    selected = list(actions)
    if len({action.site_id for action in selected}) != len(selected):
        return False
    candidate_keys = {(action.site_id, action.action_id) for action in problem.candidates}
    if any((action.site_id, action.action_id) not in candidate_keys for action in selected):
        return False
    subproblem = problem.model_copy(update={"candidates": selected})
    return _solve_model(subproblem, force_all=True) is not None


def solve_baseline(problem: AllocationProblem) -> ResponsePlan:
    """Choose feasible candidates in input order as a first-reported baseline."""
    selected: list[EligibleAction] = []
    for candidate in problem.candidates:
        proposed = [*selected, candidate]
        if _fits(problem, proposed):
            selected = proposed
    subproblem = problem.model_copy(update={"candidates": selected})
    result = _solve_model(subproblem, force_all=True)
    if result is None:
        raise RuntimeError("baseline selected an infeasible action set")
    return _plan_from_result(subproblem, result)
