"""DATA-03: the simulated resource scenarios must load and must declare themselves."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import Provenance
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.resources import ResourceScenario

FIXTURE = (
    Path(reefcommand.__file__).resolve().parent / "data/scenarios/demo_resource_scenarios.yaml"
)


@pytest.fixture(scope="module")
def scenarios() -> FixtureSet[ResourceScenario]:
    return FixtureSet[ResourceScenario].model_validate(
        yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    )


def by_id(scenarios: FixtureSet[ResourceScenario], scenario_id: str) -> ResourceScenario:
    return next(r.data for r in scenarios.records if r.record_id == scenario_id)


def test_both_demo_scenarios_are_present(scenarios) -> None:
    assert {r.record_id for r in scenarios.records} == {
        "demo_default",
        "demo_boat_b_unavailable",
    }


def test_every_shipped_scenario_is_simulated(scenarios) -> None:
    for record in scenarios.records:
        assert record.data.provenance is Provenance.SIMULATED
        assert record.data.is_simulated
        assert record.provenance.kind is Provenance.SIMULATED
        assert record.provenance.note is not None


def test_the_banner_says_simulated(scenarios) -> None:
    """This string is what the dashboard shows above any plan built from a scenario."""
    for record in scenarios.records:
        assert "Simulated" in record.data.display_banner()
        assert "not a real organization" in record.data.display_banner().lower()


def test_the_outage_variant_differs_only_in_vessel_availability(scenarios) -> None:
    """The teams still exist. They have no second vessel. That is the point."""
    default = by_id(scenarios, "demo_default")
    outage = by_id(scenarios, "demo_boat_b_unavailable")

    assert [b.available for b in default.boats] == [True, True]
    assert [b.available for b in outage.boats] == [True, False]
    assert default.dive_teams == outage.dive_teams
    assert default.inventory == outage.inventory
    assert default.budget_usd == outage.budget_usd


def test_the_outage_removes_vessel_hours(scenarios) -> None:
    def vessel_hours(scenario: ResourceScenario) -> float:
        return sum(b.operational_hours for b in scenario.boats if b.available)

    assert vessel_hours(by_id(scenarios, "demo_boat_b_unavailable")) < vessel_hours(
        by_id(scenarios, "demo_default")
    )


def test_capacity_binds_in_both_scenarios(scenarios) -> None:
    """A scenario where nothing binds produces a plan that never refuses anything."""
    for record in scenarios.records:
        scenario = record.data
        vessel_hours = sum(b.operational_hours for b in scenario.boats if b.available)
        team_hours = sum(t.available_hours for t in scenario.dive_teams)
        assert team_hours > vessel_hours


def test_dive_teams_meet_the_buddy_pair_minimum(scenarios) -> None:
    """AAUS Standards section 2.30 makes the buddy pair the in-water minimum."""
    for record in scenarios.records:
        for team in record.data.dive_teams:
            assert team.diver_count >= 2


def test_dive_hours_sit_in_the_observed_range(scenarios) -> None:
    """Derived from the Florida Keys Coral Disease Strike Team reports: 4.13 and 4.67
    in-water hours per diver-day across two fiscal years. Values outside that range
    would no longer be anchored to anything published."""
    for record in scenarios.records:
        for team in record.data.dive_teams:
            assert 4.0 <= team.available_hours <= 5.0


def test_daylight_is_not_treated_as_operating_time(scenarios) -> None:
    """13 h of August daylight in the Keys is not 13 h of vessel operations."""
    for record in scenarios.records:
        scenario = record.data
        for boat in scenario.boats:
            assert boat.operational_hours <= scenario.daylight_hours
