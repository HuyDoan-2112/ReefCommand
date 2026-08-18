"""Allocation model and OR-Tools solve tests."""

from __future__ import annotations

import pytest

from reefcommand.domain.enums import ActionClass, Cause, Priority, Provenance
from reefcommand.domain.intervention import EligibleAction, ResourceRequirement
from reefcommand.domain.resources import Boat, DiveTeam, Inventory, ResourceScenario
from reefcommand.domain.site import SiteScores
from reefcommand.optimizer.model import AllocationProblem, build_problem


def _scenario(
    *,
    boats: int = 1,
    teams: int = 1,
    boat_hours: float = 6.0,
    team_hours: float = 4.7,
    monitoring_kits: int = 1,
    daylight_hours: float = 13.0,
) -> ResourceScenario:
    return ResourceScenario(
        scenario_id="optimizer-test",
        label="Synthetic optimizer test scenario",
        provenance=Provenance.SIMULATED,
        boats=[
            Boat(
                boat_id=f"boat_{index}",
                name=f"Boat {index}",
                operational_hours=boat_hours,
            )
            for index in range(boats)
        ],
        dive_teams=[
            DiveTeam(
                team_id=f"team_{index + 1}",
                name=f"Team {index + 1}",
                diver_count=2,
                available_hours=team_hours,
            )
            for index in range(teams)
        ],
        inventory=Inventory(monitoring_kits=monitoring_kits),
        budget_usd=5000.0,
        daylight_hours=daylight_hours,
    )


def _action(site_id: str, action_id: str) -> EligibleAction:
    return EligibleAction(
        site_id=site_id,
        action_id=action_id,
        action_class=ActionClass.MONITORING,
        supporting_causes=[Cause.THERMAL],
        resources=ResourceRequirement(boats=1, dive_teams=1, dive_hours=4.0, monitoring_kits=1),
        expected_compatibility=1.0,
        provenance="Synthetic test policy record",
        priority=Priority.HIGH,
    )


def _scores() -> list[SiteScores]:
    return [
        SiteScores(site_id="site_a", ecological_value=0.9, strategic_value=0.9),
        SiteScores(site_id="site_b", ecological_value=0.4, strategic_value=0.4),
    ]


def test_build_problem_requires_scores_for_every_candidate_site() -> None:
    with pytest.raises(ValueError, match="missing SiteScores"):
        build_problem(
            [_action("site_a", "action_a")],
            _scenario(),
            [],
        )


def test_build_problem_indexes_scores_and_names() -> None:
    problem = build_problem(
        [_action("site_a", "action_a")],
        _scenario(),
        _scores(),
        site_names={"site_a": "Site A"},
    )

    assert problem.scores["site_a"].strategic_value == 0.9
    assert problem.site_names == {"site_a": "Site A"}


def test_solver_selects_highest_value_action_under_capacity() -> None:
    pytest.importorskip("ortools")
    from reefcommand.optimizer.solver import solve

    problem = AllocationProblem(
        candidates=[_action("site_a", "action_a"), _action("site_b", "action_b")],
        scenario=_scenario(),
        scores={score.site_id: score for score in _scores()},
        site_names={"site_a": "Site A", "site_b": "Site B"},
    )

    plan = solve(problem)
    second_plan = solve(problem)

    assert plan.plan_id != second_plan.plan_id
    assert [assignment.site_id for assignment in plan.assignments] == ["site_a"]
    assert plan.deferred[0].site_id == "site_b"
    assert plan.assignments[0].boat_id == "boat_0"
    assert plan.assignments[0].team_id == "team_1"
    assert plan.scenario_banner.startswith("Simulated operational capacity")
    assert plan.binding_constraints
    assert "boat_count" not in plan.deferred[0].reason


def test_baseline_uses_candidate_order_and_obeys_capacity() -> None:
    pytest.importorskip("ortools")
    from reefcommand.optimizer.solver import solve_baseline

    problem = AllocationProblem(
        candidates=[_action("site_b", "action_b"), _action("site_a", "action_a")],
        scenario=_scenario(),
        scores={score.site_id: score for score in _scores()},
    )

    plan = solve_baseline(problem)

    assert [assignment.site_id for assignment in plan.assignments] == ["site_b"]
    assert plan.total_strategic_value == 0.4


def test_assignments_are_keyed_by_site_and_action() -> None:
    from reefcommand.optimizer.solver import solve

    scenario = _scenario(
        boats=2,
        teams=2,
        monitoring_kits=2,
    )
    problem = AllocationProblem(
        candidates=[
            _action("site_a", "intensive_monitoring"),
            _action("site_b", "intensive_monitoring"),
        ],
        scenario=scenario,
        scores={score.site_id: score for score in _scores()},
    )

    plan = solve(problem)

    assert len(plan.assignments) == 2
    assert len({assignment.boat_id for assignment in plan.assignments}) == 2
    assert len({assignment.team_id for assignment in plan.assignments}) == 2


def test_daylight_limits_each_parallel_resource_not_the_fleet_total() -> None:
    from reefcommand.optimizer.solver import solve

    scenario = _scenario(
        boats=2,
        teams=2,
        boat_hours=8.0,
        team_hours=8.0,
        monitoring_kits=2,
        daylight_hours=4.5,
    )
    problem = AllocationProblem(
        candidates=[
            _action("site_a", "action_a"),
            _action("site_b", "action_b"),
        ],
        scenario=scenario,
        scores={score.site_id: score for score in _scores()},
    )

    plan = solve(problem)

    assert len(plan.assignments) == 2
    assert sum(assignment.estimated_hours for assignment in plan.assignments) == 8.0


def test_solver_is_stable_across_identical_runs() -> None:
    from reefcommand.optimizer.solver import solve

    problem = AllocationProblem(
        candidates=[_action("site_a", "action_a"), _action("site_b", "action_b")],
        scenario=_scenario(),
        scores={
            "site_a": SiteScores(site_id="site_a", ecological_value=0.5, strategic_value=0.5),
            "site_b": SiteScores(site_id="site_b", ecological_value=0.5, strategic_value=0.5),
        },
    )

    selections = [
        [
            (item.site_id, item.action_id, item.boat_id, item.team_id)
            for item in solve(problem).assignments
        ]
        for _ in range(8)
    ]

    assert all(selection == selections[0] for selection in selections)
