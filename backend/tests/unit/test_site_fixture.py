"""DATA-02: the site fixture must load as real ReefSite objects, with honest provenance.

Run from the backend environment:
    uv run pytest tests/unit/test_site_fixture.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import MonitoringProgram, Provenance
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.site import ReefSite

FIXTURE = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"

STUDY_AREA = frozenset(
    {
        "carysfort",
        "horseshoe",
        "cheeca_rocks",
        "sombrero",
        "newfound_harbor",
        "looe_key",
        "eastern_dry_rocks",
    }
)


@pytest.fixture(scope="module")
def sites() -> FixtureSet[ReefSite]:
    return FixtureSet[ReefSite].model_validate(yaml.safe_load(FIXTURE.read_text(encoding="utf-8")))


def test_fixture_covers_exactly_the_study_area(sites) -> None:
    assert {record.record_id for record in sites.records} == STUDY_AREA


def test_every_record_loads_as_a_reef_site(sites) -> None:
    for record in sites.records:
        assert isinstance(record.data, ReefSite)
        assert record.data.site_id == record.record_id


def test_coordinates_are_serialized_for_the_api_contract(sites) -> None:
    """Nested storage must not remove the flat coordinates from API payloads."""
    for record in sites.records:
        payload = record.data.model_dump()
        assert payload["latitude"] == record.data.location.latitude
        assert payload["longitude"] == record.data.location.longitude


def test_no_persisted_record_claims_to_be_live(sites) -> None:
    """The one failure mode the project's rules single out."""
    for record in sites.records:
        site = record.data
        for kind in (
            record.provenance.kind,
            site.location.provenance.kind,
            site.measurements.provenance.kind,
            site.restoration_investment.provenance.kind,
        ):
            assert kind is not Provenance.LIVE


def test_restoration_investment_is_labeled_simulated_everywhere(sites) -> None:
    """It is the only invented number in this fixture and it must say so."""
    for record in sites.records:
        provenance = record.data.restoration_investment.provenance
        assert provenance.kind is Provenance.SIMULATED
        assert provenance.note is not None
        assert "SIMULATED" in provenance.note


def test_externally_sourced_blocks_carry_a_fetch_timestamp(sites) -> None:
    for record in sites.records:
        site = record.data
        assert site.location.provenance.fetched_at is not None
        assert site.measurements.provenance.fetched_at is not None
        assert site.location.provenance.source_url is not None
        assert site.measurements.provenance.source_url is not None


def test_measurements_declare_their_programme_and_sampling(sites) -> None:
    """Programme is first-class because CREMP and NCRMP are not interchangeable."""
    for record in sites.records:
        sampling = record.data.measurements.sampling
        assert sampling.program in set(MonitoringProgram)
        assert sampling.sample_n >= 1
        assert sampling.reference_years
        assert sampling.matching_method
        assert sampling.richness_definition


def test_spatially_matched_sites_record_how_far(sites) -> None:
    """A named match is distance zero. A buffer match must state its radius."""
    for record in sites.records:
        sampling = record.data.measurements.sampling
        if sampling.program is MonitoringProgram.NCRMP:
            assert sampling.matching_distance_km > 0.0
            assert "buffer" in sampling.matching_method
            assert not sampling.station_ids
        else:
            assert sampling.matching_distance_km == 0.0
            assert sampling.station_ids


def test_millepora_inclusion_matches_the_programme(sites) -> None:
    """CREMP cover includes Millepora, the NCRMP figures here do not."""
    for record in sites.records:
        sampling = record.data.measurements.sampling
        assert sampling.includes_millepora is (sampling.program is MonitoringProgram.CREMP)


def test_coordinates_fall_inside_the_florida_keys(sites) -> None:
    for record in sites.records:
        assert 24.3 <= record.data.latitude <= 25.5
        assert -82.2 <= record.data.longitude <= -80.0


def test_every_location_states_its_point_convention(sites) -> None:
    """These are areas reduced to points. The reduction is never implied."""
    for record in sites.records:
        assert record.data.location.location_basis


def test_both_programmes_are_present(sites) -> None:
    """If this ever fails, the two-programme caveat has silently stopped applying."""
    programs = {record.data.measurements.sampling.program for record in sites.records}
    assert programs == set(MonitoringProgram)
