"""The closed loop, driven through the real entry point.

This is the demo, as a test.
If this file passes, the three minutes on stage work.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reefcommand.domain.enums import ActionClass
from reefcommand.domain.resources import Boat
from reefcommand.ingestion.field_reports import load_demo_updates
from reefcommand.orchestration.events import NewEvidence, ResourceChange
from reefcommand.orchestration.pipeline import load_scenario, run, state_for_plan
from reefcommand.orchestration.replanner import handle, is_plan_still_feasible

pytestmark = pytest.mark.e2e


SITE_IDS = [
    "carysfort",
    "horseshoe",
    "cheeca_rocks",
    "sombrero",
    "newfound_harbor",
    "looe_key",
    "eastern_dry_rocks",
]


def test_initial_plan_is_produced_within_capacity() -> None:
    plan = run("demo_default", SITE_IDS)

    assert plan.assignments
    assert plan.scenario_id == "demo_default"
    assert all(assignment.requires_manager_approval for assignment in plan.assignments)
    assert all(
        assignment.action_class is not ActionClass.BIOSECURITY_WORKFLOW
        for assignment in plan.assignments
    )
    state = state_for_plan(plan.plan_id)
    assert state is not None
    scenario = load_scenario(plan.scenario_id)
    actions = {(action.site_id, action.action_id): action for action in state.problem.candidates}
    team_hours: dict[str, float] = {}
    for assignment in plan.assignments:
        action = actions[(assignment.site_id, assignment.action_id)]
        assert assignment.team_id is not None
        team_hours[assignment.team_id] = (
            team_hours.get(assignment.team_id, 0.0) + action.resources.dive_hours
        )
    limits = {team.team_id: team.available_hours for team in scenario.dive_teams}
    assert all(hours <= limits[team_id] for team_id, hours in team_hours.items())


def test_new_field_report_changes_the_plan() -> None:
    """Submit the Cheeca Rocks tissue-loss report and expect a different allocation."""
    initial = run("demo_default", SITE_IDS)
    revised = handle(
        NewEvidence(
            received_at=datetime.now(UTC),
            report=load_demo_updates()[0],
        ),
        initial,
    )

    assert revised.replan_trigger == "new_evidence:cheeca_rocks-2023-09-15-update"
    assert revised.replan_latency_ms is not None
    assert any(
        assignment.site_id == "cheeca_rocks" and assignment.action_id == "targeted_disease_survey"
        for assignment in revised.assignments
    )


def test_boat_becoming_unavailable_triggers_recompute() -> None:
    """The plan becomes infeasible and the system detects it without being asked."""
    initial = run("demo_default", SITE_IDS)
    assert not is_plan_still_feasible(initial, "demo_boat_b_unavailable")
    revised = handle(
        ResourceChange(
            received_at=datetime.now(UTC),
            scenario_id="demo_boat_b_unavailable",
            description="Boat B out of service",
        ),
        initial,
    )

    assert revised.scenario_id == "demo_boat_b_unavailable"
    assert revised.replan_trigger == "resource_change:demo_boat_b_unavailable"
    assert all(assignment.boat_id == "boat_a" for assignment in revised.assignments)
    state = state_for_plan(revised.plan_id)
    assert state is not None
    assert state.trace.parent_plan_id == initial.plan_id
    assert [step.stage.value for step in state.trace.steps] == ["optimizer"]
    assert state.trace.steps[0].inputs["reused_evidence"] is True


def test_missing_process_state_is_unknown_not_infeasible() -> None:
    plan = run("demo_default", SITE_IDS)
    unknown = plan.model_copy(update={"plan_id": "not-retained"})

    assert is_plan_still_feasible(unknown, "demo_default") is None


def test_different_scenario_with_more_capacity_remains_feasible(monkeypatch) -> None:
    from reefcommand.orchestration import replanner

    plan = run("demo_default", SITE_IDS)
    default = load_scenario("demo_default")
    expanded = default.model_copy(
        update={
            "scenario_id": "demo_expanded_capacity",
            "boats": [
                *default.boats,
                Boat(
                    boat_id="boat_c",
                    name="Boat C",
                    operational_hours=default.daylight_hours,
                ),
            ],
        }
    )
    monkeypatch.setattr(replanner, "load_scenario", lambda _scenario_id: expanded)

    assert replanner.is_plan_still_feasible(plan, "demo_expanded_capacity") is True


def test_plan_response_carries_the_simulated_data_banner() -> None:
    """Simulated capacity is never presented as real, including through the API."""
    plan = run("demo_default", SITE_IDS)

    assert "Simulated operational capacity" in plan.scenario_banner
    assert "not a real" in plan.scenario_banner.lower()
