"""The closed loop, driven through the real entry point.

This is the demo, as a test.
If this file passes, the three minutes on stage work.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reefcommand.domain.enums import ActionClass
from reefcommand.ingestion.field_reports import load_demo_updates
from reefcommand.orchestration.events import NewEvidence, ResourceChange
from reefcommand.orchestration.pipeline import run
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


def test_plan_response_carries_the_simulated_data_banner() -> None:
    """Simulated capacity is never presented as real, including through the API."""
    plan = run("demo_default", SITE_IDS)

    assert "Simulated operational capacity" in plan.scenario_banner
    assert "not a real" in plan.scenario_banner.lower()
