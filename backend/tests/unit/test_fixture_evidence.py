"""Fixture-backed disease, runoff, and physical evidence tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.site import ReefSite
from reefcommand.evidence import disease, physical, runoff
from reefcommand.ingestion import rainfall, storm_vessel

SITES_FILE = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"


@pytest.fixture(scope="module")
def sites() -> dict[str, ReefSite]:
    fixture = FixtureSet[ReefSite].model_validate(
        yaml.safe_load(SITES_FILE.read_text(encoding="utf-8"))
    )
    return {record.data.site_id: record.data for record in fixture.records}


def _observation(site_id: str, **updates: object) -> StructuredObservation:
    values: dict[str, object] = {
        "report_id": f"{site_id}-evidence-test",
        "site_id": site_id,
        "observed_at": datetime(2023, 9, 15, tzinfo=UTC),
    }
    values.update(updates)
    return StructuredObservation.model_validate(values)


def test_disease_uses_lesions_and_nearby_tracker_context(sites) -> None:
    site = sites["cheeca_rocks"]
    observation = _observation(
        site.site_id,
        tissue_loss_observed=True,
        lesion_description=(
            "A distinct advancing margin separates living tissue from bare skeleton."
        ),
        spatial_progression="Several colonies lost additional tissue since the previous dive.",
        affected_taxa=["Orbicella faveolata"],
    )

    evidence = disease.assess(site, [observation])

    assert evidence.cause is Cause.DISEASE
    assert 0.0 < evidence.support <= 1.0
    assert evidence.confidence == pytest.approx(disease.DISEASE_INPUT_CONFIDENCE)
    assert evidence.citations
    assert any(citation.review_status == "synthetic_example" for citation in evidence.citations)
    assert "not confirmation" in evidence.rationale


def test_disease_has_no_support_without_field_observations(sites) -> None:
    evidence = disease.assess(sites["cheeca_rocks"], [])

    assert evidence.support == 0.0
    assert evidence.confidence == 0.0
    assert evidence.citations == []


def test_runoff_labels_synthetic_rainfall(sites) -> None:
    site = sites["cheeca_rocks"]
    observation = _observation(site.site_id, turbidity_note="Water was visibly cloudy.")

    evidence = runoff.assess(site, [observation])

    assert evidence.cause is Cause.RUNOFF
    assert 0.0 <= evidence.support <= 1.0
    assert evidence.citations[0].provenance is Provenance.SYNTHETIC
    assert "synthetic fallback" in evidence.rationale.lower()


def test_physical_combines_breakage_and_synthetic_activity(sites) -> None:
    site = sites["sombrero"]
    observation = _observation(site.site_id, broken_coral_observed=True)

    evidence = physical.assess(site, [observation])

    assert evidence.cause is Cause.PHYSICAL
    assert 0.0 < evidence.support <= 1.0
    assert evidence.citations
    assert all(citation.provenance is Provenance.SYNTHETIC for citation in evidence.citations)
    assert "synthetic fallback" in evidence.rationale.lower()


def test_synthetic_adapters_are_stable_and_validate_days() -> None:
    first = rainfall.synthetic_rainfall("cheeca_rocks", 7)
    second = rainfall.synthetic_rainfall("cheeca_rocks", 7)
    assert first == second
    assert first.provenance is Provenance.SYNTHETIC

    storms = storm_vessel.fetch_storm_history("cheeca_rocks", 30)
    vessels = storm_vessel.fetch_vessel_activity("cheeca_rocks", 30)
    assert all(storm.provenance is Provenance.SYNTHETIC for storm in storms)
    assert vessels.provenance is Provenance.SYNTHETIC

    with pytest.raises(ValueError, match="at least 1"):
        rainfall.synthetic_rainfall("cheeca_rocks", 0)
    with pytest.raises(ValueError, match="at least 1"):
        storm_vessel.fetch_storm_history("cheeca_rocks", 0)
