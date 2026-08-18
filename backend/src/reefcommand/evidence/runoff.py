"""LLM runoff investigator grounded by the local rainfall tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime, time
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation, EvidenceFinding
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.rainfall import RainfallSignal
from reefcommand.llm.client import complete_structured
from reefcommand.tools.contracts import EvidenceSnapshot, ToolResult

cause: Cause = Cause.RUNOFF
_RAINFALL_TOOL_NAME = "rainfall"


class RunoffAssessment(BaseModel):
    """The only runoff judgment the model is allowed to return."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    support: float = Field(ge=0.0, le=1.0, description="Runoff support score, not a probability.")
    confidence: float = Field(ge=0.0, le=1.0)
    display_summary: str = Field(min_length=1, max_length=180)
    key_findings: list[EvidenceFinding] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, description="Evidence-grounded explanation.")


class RunoffCompleter(Protocol):
    def __call__(
        self,
        system: str,
        user: str,
        schema: type[RunoffAssessment],
    ) -> RunoffAssessment:
        """Return one validated runoff assessment."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[RunoffAssessment],
) -> RunoffAssessment:
    return complete_structured(system, user, schema)


def _citations(
    observations: list[StructuredObservation],
    result: ToolResult[object],
    signal: RainfallSignal,
) -> list[EvidenceCitation]:
    citations = [
        EvidenceCitation(
            source=(
                observation.provenance_metadata.source
                if observation.provenance_metadata
                else "Field observation report"
            ),
            reference=(
                observation.provenance_metadata.source_url
                if observation.provenance_metadata and observation.provenance_metadata.source_url
                else observation.report_id
            ),
            observed_at=observation.observed_at,
            provenance=(
                observation.provenance_metadata.kind
                if observation.provenance_metadata
                else Provenance.SYNTHETIC
            ),
        )
        for observation in observations
    ]
    citations.append(
        EvidenceCitation(
            source=result.source,
            reference=result.source_url,
            observed_at=datetime.combine(signal.window_end, time.min, tzinfo=UTC),
            provenance=result.provenance,
        )
    )
    return citations


class RunoffAgent:
    """Assess runoff support from field reports and one aligned rainfall tool result."""

    cause = Cause.RUNOFF

    def __init__(self, completer: RunoffCompleter | None = None) -> None:
        self._complete = completer or _default_complete

    def assess(
        self,
        site: ReefSite,
        observations: list[StructuredObservation],
        snapshot: EvidenceSnapshot,
    ) -> CauseEvidence:
        if snapshot.site_id != site.site_id:
            raise ValueError("runoff snapshot site_id must match the requested site")
        result = snapshot.result(_RAINFALL_TOOL_NAME)
        signal = RainfallSignal.model_validate(result.data)
        if signal.site_id != site.site_id:
            raise ValueError("rainfall result site_id must match the requested site")
        site_observations = [
            observation for observation in observations if observation.site_id == site.site_id
        ]
        system = (
            "You are the runoff evidence investigator for a coral reef decision-support system. "
            "Assess runoff support only from the supplied field observations and rainfall facts. "
            "Do not infer an unreported pollution source, invent citations, treat support as a "
            "probability, or claim causation from rainfall alone. Return only the requested "
            "structured fields."
        )
        user = (
            f"Site:\n{json.dumps(site.model_dump(mode='json'), indent=2)}\n\n"
            "Field observations:\n"
            f"{json.dumps([item.model_dump(mode='json') for item in site_observations], indent=2)}"
            "\n\n"
            f"Rainfall tool result:\n{json.dumps(signal.model_dump(mode='json'), indent=2)}\n\n"
            "Give a 0 to 1 runoff support score, a 0 to 1 confidence score, one display_summary "
            "sentence under 180 characters, 1 to 3 key_findings under 110 characters each, and "
            "a full audit rationale. Every statement must name only facts present above."
        )
        assessment = self._complete(system, user, RunoffAssessment)
        rationale_parts = [assessment.rationale]
        if result.provenance in (Provenance.SIMULATED, Provenance.SYNTHETIC):
            rationale_parts.append(
                "Rainfall input is a synthetic repository fixture, not a live measurement."
            )
        if result.stale:
            rationale_parts.append(
                f"Rainfall data is marked stale: {result.note or 'no reason supplied'}"
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
            citations=_citations(site_observations, result, signal),
            computed_at=datetime.now(UTC),
        )


def assess(
    site: ReefSite,
    observations: list[StructuredObservation],
    snapshot: EvidenceSnapshot,
    *,
    completer: RunoffCompleter | None = None,
) -> CauseEvidence:
    """Convenience entry point for the runoff agent."""
    return RunoffAgent(completer).assess(site, observations, snapshot)
