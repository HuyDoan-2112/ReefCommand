"""Allocation model and OR-Tools solve tests."""

from __future__ import annotations

import pytest

from reefcommand.domain.enums import ActionClass, Cause, Priority, Provenance
from reefcommand.domain.intervention import EligibleAction, ResourceRequirement
from reefcommand.domain.resources import Boat, DiveTeam, Inventory, ResourceScenario
from reefcommand.domain.site import SiteScores
from reefcommand.optimizer.model import AllocationProblem, build_problem


def _scenario(*, boats: int = 1, boat_hours: float = 6.0) -> ResourceScenario:
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
                team_id="team_1",
                name="Team 1",
                diver_count=2,
                available_hours=4.7,
            )
        ],
        inventory=Inventory(monitoring_kits=1),
        budget_usd=5000.0,
        daylight_hours=13.0,
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

    assert [assignment.site_id for assignment in plan.assignments] == ["site_a"]
    assert plan.deferred[0].site_id == "site_b"
    assert plan.assignments[0].boat_id == "boat_0"
    assert plan.assignments[0].team_id == "team_1"
    assert plan.scenario_banner.startswith("Simulated operational capacity")
    assert plan.binding_constraints


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
