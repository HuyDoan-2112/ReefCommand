"""DATA-06: the demo field reports and their structured forms.

Two things are pinned here. First, the reconstructed reports load
deterministically, one per site, plus the Cheeca Rocks update that drives
re-planning. Second, every shipped report is labeled synthetic and carries the
source it was derived from, and the Cheeca disease update describes tissue loss
without claiming a confirmed SCTLD diagnosis.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import Provenance
from reefcommand.domain.observation import FieldReport, StructuredObservation
from reefcommand.domain.provenance import FixtureSet
from reefcommand.ingestion.field_reports import (
    load_demo_reports,
    load_demo_updates,
    structure,
)

OBSERVATIONS_DIR = Path(reefcommand.__file__).resolve().parent / "data/observations"


def _reports(name: str) -> FixtureSet[FieldReport]:
    return FixtureSet[FieldReport].model_validate(
        yaml.safe_load((OBSERVATIONS_DIR / name).read_text(encoding="utf-8"))
    )


def _observations() -> FixtureSet[StructuredObservation]:
    return FixtureSet[StructuredObservation].model_validate(
        yaml.safe_load((OBSERVATIONS_DIR / "demo_structured_observations.yaml").read_text("utf-8"))
    )


def test_one_initial_report_per_site(demo_site_ids) -> None:
    reports = load_demo_reports(demo_site_ids)
    assert [report.site_id for report in reports] == demo_site_ids
    assert len({report.report_id for report in reports}) == len(demo_site_ids)


def test_reports_are_returned_in_requested_order() -> None:
    reports = load_demo_reports(["sombrero", "carysfort"])
    assert [report.site_id for report in reports] == ["sombrero", "carysfort"]


def test_unknown_site_fails_loudly() -> None:
    with pytest.raises(ValueError, match="no demo field report"):
        load_demo_reports(["atlantis"])


def test_every_shipped_report_is_labeled_synthetic() -> None:
    for name in ("demo_field_reports.yaml", "demo_evidence_update.yaml"):
        fixtures = _reports(name)
        for record in fixtures.records:
            assert record.data.provenance is Provenance.SYNTHETIC
            assert record.provenance.kind is Provenance.SYNTHETIC
            assert record.provenance.note is not None
            assert record.provenance.source


def test_every_structured_observation_is_labeled_synthetic() -> None:
    for record in _observations().records:
        assert record.provenance.kind is Provenance.SYNTHETIC
        assert record.provenance.note is not None


def test_update_is_separate_from_the_initial_reports() -> None:
    updates = load_demo_updates()
    assert len(updates) == 1
    update = updates[0]
    assert update.site_id == "cheeca_rocks"
    assert update.report_id.endswith("update")

    initial = load_demo_reports(["cheeca_rocks"])[0]
    assert initial.report_id != update.report_id
    assert update.observed_at > initial.observed_at


def test_structure_matches_each_report() -> None:
    for report in [*load_demo_reports(_all_site_ids()), *load_demo_updates()]:
        observation = structure(report)
        assert observation.report_id == report.report_id
        assert observation.site_id == report.site_id
        assert observation.observed_at == report.observed_at


def test_structure_of_unknown_report_fails_loudly() -> None:
    stray = FieldReport(
        report_id="not-a-demo-report",
        site_id="sombrero",
        observed_at=datetime.fromisoformat("2023-08-01T10:00:00-04:00"),
        observer="Reconstructed demo observer",
        text="A report with no structuring fixture.",
    )
    with pytest.raises(ValueError, match="no structuring fixture"):
        structure(stray)


def test_initial_cheeca_report_is_bleaching_not_disease() -> None:
    initial = load_demo_reports(["cheeca_rocks"])[0]
    observation = structure(initial)
    assert observation.tissue_loss_observed is False
    assert observation.lesion_description is None
    assert observation.bleaching_pct == 100.0


def test_cheeca_update_carries_a_disease_signal() -> None:
    update = load_demo_updates()[0]
    observation = structure(update)
    assert observation.tissue_loss_observed is True
    assert observation.lesion_description is not None
    assert "skeleton" in observation.lesion_description.lower()


def test_cheeca_update_does_not_claim_confirmed_sctld() -> None:
    observation = structure(load_demo_updates()[0])
    assert observation.extraction_notes is not None
    assert "not a confirmed sctld" in observation.extraction_notes.lower()


def test_demo_reports_load_deterministically(demo_site_ids) -> None:
    assert load_demo_reports(demo_site_ids) == load_demo_reports(demo_site_ids)
    assert load_demo_updates() == load_demo_updates()


def _all_site_ids() -> list[str]:
    return [
        "carysfort",
        "horseshoe",
        "cheeca_rocks",
        "sombrero",
        "newfound_harbor",
        "looe_key",
        "eastern_dry_rocks",
    ]
