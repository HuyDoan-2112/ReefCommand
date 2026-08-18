"""Schema-constrained LLM structuring for free-text field reports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.observation import FieldReport, StructuredObservation
from reefcommand.domain.provenance import EXTERNAL_PROVENANCE, ProvenanceMetadata
from reefcommand.llm.client import complete_structured


class ExtractedObservation(BaseModel):
    """Only report-derived signals the model may produce.

    Report identity and provenance are copied from the submitted report by the
    application. The model cannot rewrite them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    paling_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    bleaching_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    tissue_loss_observed: bool | None = None
    lesion_description: str | None = Field(default=None, max_length=300)
    affected_taxa: list[str] = Field(default_factory=list, max_length=12)
    spatial_progression: str | None = Field(default=None, max_length=300)
    broken_coral_observed: bool | None = None
    turbidity_note: str | None = Field(default=None, max_length=300)
    sediment_note: str | None = Field(default=None, max_length=300)
    compared_to_previous_dive: str | None = Field(default=None, max_length=300)
    extraction_notes: str | None = Field(default=None, max_length=500)
    extraction_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Uncalibrated model self-assessment of extraction clarity, not evidence confidence."
        ),
    )


class StructuredReportExtraction(BaseModel):
    """The observation plus the model's uncalibrated extraction-confidence estimate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observation: StructuredObservation
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class ReportCompleter(Protocol):
    def __call__(
        self,
        system: str,
        user: str,
        schema: type[ExtractedObservation],
    ) -> ExtractedObservation:
        """Return one validated extraction."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[ExtractedObservation],
) -> ExtractedObservation:
    return complete_structured(system, user, schema)


def structure_live(
    report: FieldReport,
    *,
    completer: ReportCompleter | None = None,
) -> StructuredReportExtraction:
    """Extract only explicitly reported observations from free text with an LLM."""
    system = (
        "You structure diver field notes for a coral reef decision-support system. "
        "Extract only facts explicitly stated in the report. Do not diagnose disease, "
        "infer a percentage, convert vague quantities into numbers, or treat an unmentioned "
        "condition as false. Use null for anything not reported. Preserve uncertainty in "
        "extraction_notes. Return only the requested structured fields."
    )
    user = (
        "Raw field report:\n"
        f"{json.dumps(report.model_dump(mode='json'), indent=2)}\n\n"
        "Rules:\n"
        "- Percent fields require an explicit numeric percentage in the report.\n"
        "- A clear denial such as 'no broken coral' may be false; silence must be null.\n"
        "- affected_taxa contains only taxa named by the observer.\n"
        "- lesion_description describes morphology without assigning a diagnosis.\n"
        "- extraction_notes briefly identify ambiguity or omitted inferences.\n"
        "- extraction_confidence is your uncalibrated confidence that the fields "
        "faithfully reflect the text."
    )
    extraction = (completer or _default_complete)(system, user, ExtractedObservation)
    metadata = ProvenanceMetadata(
        kind=report.provenance,
        source=f"LLM structure of field report {report.report_id}",
        observed_at=report.observed_at,
        fetched_at=datetime.now(UTC) if report.provenance in EXTERNAL_PROVENANCE else None,
        note=(
            None
            if report.provenance in EXTERNAL_PROVENANCE
            else (
                "Structured by the configured LLM from the submitted report. "
                "The source report remains the authority and the extraction requires review."
            )
        ),
    )
    observation = StructuredObservation(
        report_id=report.report_id,
        site_id=report.site_id,
        observed_at=report.observed_at,
        **extraction.model_dump(),
        provenance_metadata=metadata,
    )
    return StructuredReportExtraction(
        observation=observation,
        extraction_confidence=extraction.extraction_confidence,
    )
