"""Tests for schema-constrained free-text report structuring."""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.domain.enums import Provenance
from reefcommand.domain.observation import FieldReport
from reefcommand.evidence.disease import DiseaseAssessment
from reefcommand.ingestion.llm_field_reports import (
    ExtractedObservation,
    StructuredReportExtraction,
    structure_live,
)


class FakeCompleter:
    def __init__(self) -> None:
        self.system = ""
        self.user = ""

    def __call__(
        self,
        system: str,
        user: str,
        schema: type[ExtractedObservation],
    ) -> ExtractedObservation:
        self.system = system
        self.user = user
        return schema(
            paling_pct=None,
            bleaching_pct=None,
            tissue_loss_observed=True,
            lesion_description="Sharp boundary between living tissue and bare skeleton.",
            affected_taxa=["brain coral", "star coral"],
            spatial_progression="Spreading since the August bleaching visit.",
            broken_coral_observed=None,
            turbidity_note=None,
            sediment_note=None,
            compared_to_previous_dive="New tissue loss since the previous visit.",
            extraction_notes="No numeric affected-area percentage was reported.",
            extraction_confidence=0.96,
        )


def _report() -> FieldReport:
    return FieldReport(
        report_id="messy-cheeca-001",
        site_id="cheeca_rocks",
        observed_at=datetime(2023, 9, 15, 14, 5, tzinfo=UTC),
        observer="Demo diver",
        text=(
            "Back at Cheeca. Brain and star corals have spreading tissue loss with a sharp "
            "line to bare skeleton. I did not estimate a percent."
        ),
        provenance=Provenance.SYNTHETIC,
    )


def test_live_structurer_preserves_identity_and_unknown_values() -> None:
    completer = FakeCompleter()

    extraction = structure_live(_report(), completer=completer)

    assert isinstance(extraction, StructuredReportExtraction)
    observation = extraction.observation
    assert observation.report_id == "messy-cheeca-001"
    assert observation.site_id == "cheeca_rocks"
    assert observation.bleaching_pct is None
    assert observation.broken_coral_observed is None
    assert observation.tissue_loss_observed is True
    assert extraction.extraction_confidence == 0.96
    assert observation.provenance_metadata is not None
    assert observation.provenance_metadata.kind is Provenance.SYNTHETIC
    assert "Use null" in completer.system
    assert "I did not estimate a percent" in completer.user


def test_extraction_schema_is_not_an_investigator_assessment() -> None:
    assert "support" not in ExtractedObservation.model_fields
    assert "confidence" not in ExtractedObservation.model_fields
    assert "report_id" not in ExtractedObservation.model_fields
    assert "support" in DiseaseAssessment.model_fields
