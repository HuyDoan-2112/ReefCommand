"""LLM disease investigator grounded by the local AGRRA evidence tool.

The agent interprets lesion descriptions and nearby tracker records. It returns
only a support score, confidence, and rationale. Citations are assembled from
validated inputs by this module, so the model cannot fabricate sources.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation, EvidenceFinding
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.agrra_sctld import NearbyRecords
from reefcommand.llm.client import complete_structured
from reefcommand.tools.contracts import EvidenceSnapshot, ToolResult

cause: Cause = Cause.DISEASE
DEFAULT_SEARCH_RADIUS_KM = 25.0
_AGRRA_TOOL_NAME = "agrra_sctld"


class DiseaseAssessment(BaseModel):
    """The only disease judgment the model is allowed to return."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    support: float = Field(
        ge=0.0,
        le=1.0,
        description="Disease support score, not a probability.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the support score given the supplied evidence.",
    )
    display_summary: str = Field(min_length=1, max_length=180)
    key_findings: list[EvidenceFinding] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, description="Evidence-grounded explanation.")


class DiseaseCompleter(Protocol):
    """The structured model boundary, replaceable by a test double."""

    def __call__(
        self,
        system: str,
        user: str,
        schema: type[DiseaseAssessment],
    ) -> DiseaseAssessment:
        """Return one validated disease assessment."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[DiseaseAssessment],
) -> DiseaseAssessment:
    return complete_structured(system, user, schema)


def _observation_citations(observations: list[StructuredObservation]) -> list[EvidenceCitation]:
    citations: list[EvidenceCitation] = []
    for observation in observations:
        metadata = observation.provenance_metadata
        citations.append(
            EvidenceCitation(
                source=metadata.source if metadata else "Field observation report",
                reference=(
                    metadata.source_url
                    if metadata and metadata.source_url
                    else observation.report_id
                ),
                observed_at=observation.observed_at,
                provenance=metadata.kind if metadata else Provenance.SYNTHETIC,
            )
        )
    return citations


def _record_observed_at(record_date: date) -> datetime:
    return datetime.combine(record_date, time.min, tzinfo=UTC)


def _agrra_citations(result: ToolResult[object], nearby: NearbyRecords) -> list[EvidenceCitation]:
    if not nearby.records:
        return [
            EvidenceCitation(
                source=result.source,
                reference=result.source_url,
                provenance=result.provenance,
            )
        ]

    citations: list[EvidenceCitation] = []
    for record in nearby.records:
        metadata = record.provenance_metadata
        citations.append(
            EvidenceCitation(
                source=metadata.source if metadata else result.source,
                reference=(
                    metadata.source_url if metadata and metadata.source_url else record.record_id
                ),
                observed_at=_record_observed_at(record.submitted_on),
                review_status=record.review_status,
                reporting_organization=record.reporting_organization,
                provenance=record.provenance,
            )
        )
    return citations


class DiseaseAgent:
    """Assess disease support from field observations and one aligned tool result."""

    cause = Cause.DISEASE

    def __init__(self, completer: DiseaseCompleter | None = None) -> None:
        self._complete = completer or _default_complete

    def assess(
        self,
        site: ReefSite,
        observations: list[StructuredObservation],
        snapshot: EvidenceSnapshot,
    ) -> CauseEvidence:
        """Return a grounded disease assessment for one immutable snapshot."""
        if snapshot.site_id != site.site_id:
            raise ValueError("disease snapshot site_id must match the requested site")

        result = snapshot.result(_AGRRA_TOOL_NAME)
        nearby = NearbyRecords.model_validate(result.data)
        if nearby.site_id != site.site_id:
            raise ValueError("AGRRA result site_id must match the requested site")
        if len(nearby.records) != len(nearby.distances_km):
            raise ValueError("AGRRA result records and distances must have the same length")
        site_observations = [
            observation for observation in observations if observation.site_id == site.site_id
        ]
        system = (
            "You are the disease evidence investigator for a coral reef decision-support system. "
            "Assess disease support only from the supplied field observations and AGRRA facts. "
            "A nearby record is supporting context, not confirmation of disease at this site. "
            "Do not diagnose SCTLD, infer facts that are not supplied, create citations, or "
            "treat support as a probability. Return only the requested structured fields."
        )
        user = (
            f"Site:\n{json.dumps(site.model_dump(mode='json'), indent=2)}\n\n"
            "Field observations:\n"
            f"{json.dumps([item.model_dump(mode='json') for item in site_observations], indent=2)}"
            "\n\n"
            f"AGRRA tool result:\n{json.dumps(nearby.model_dump(mode='json'), indent=2)}\n\n"
            "Give a 0 to 1 disease support score, a 0 to 1 confidence score, one display_summary "
            "sentence under 180 characters, 1 to 3 key_findings under 110 characters each, and "
            "a full audit rationale. Every statement must name only facts present above."
        )
        assessment = self._complete(system, user, DiseaseAssessment)

        rationale_parts = [assessment.rationale]
        if result.provenance in (Provenance.SIMULATED, Provenance.SYNTHETIC):
            rationale_parts.append(
                "AGRRA input is a synthetic repository fixture and is not a real reviewed record."
            )
        if result.stale:
            rationale_parts.append(
                f"AGRRA data is marked stale: {result.note or 'no reason supplied'}"
            )
        if not site_observations:
            rationale_parts.append("No field observations were supplied for this site.")

        return CauseEvidence(
            cause=self.cause,
            support=assessment.support,
            confidence=assessment.confidence,
            display_summary=assessment.display_summary,
            key_findings=assessment.key_findings,
            rationale=" ".join(rationale_parts),
            citations=_observation_citations(site_observations) + _agrra_citations(result, nearby),
            computed_at=datetime.now(UTC),
        )


def assess(
    site: ReefSite,
    observations: list[StructuredObservation],
    snapshot: EvidenceSnapshot,
    *,
    completer: DiseaseCompleter | None = None,
) -> CauseEvidence:
    """Convenience entry point for the disease agent."""
    return DiseaseAgent(completer).assess(site, observations, snapshot)
