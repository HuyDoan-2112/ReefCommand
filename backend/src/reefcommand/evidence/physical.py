"""LLM physical-damage investigator grounded by storm and vessel tools."""

from __future__ import annotations

import json
from datetime import UTC, datetime, time
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation, EvidenceFinding
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.storm_vessel import StormEvent, VesselActivity
from reefcommand.llm.client import complete_structured
from reefcommand.tools.contracts import EvidenceSnapshot, ToolResult

cause: Cause = Cause.PHYSICAL
_STORM_TOOL_NAME = "storm_history"
_VESSEL_TOOL_NAME = "vessel_activity"
_UNCORROBORATED_SUPPORT_CAP = 0.2


class PhysicalAssessment(BaseModel):
    """The only physical-damage judgment the model is allowed to return."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    support: float = Field(
        ge=0.0,
        le=1.0,
        description="Physical-damage support score, not a probability.",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    display_summary: str = Field(min_length=1, max_length=180)
    key_findings: list[EvidenceFinding] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, description="Evidence-grounded explanation.")


class PhysicalCompleter(Protocol):
    def __call__(
        self,
        system: str,
        user: str,
        schema: type[PhysicalAssessment],
    ) -> PhysicalAssessment:
        """Return one validated physical-damage assessment."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[PhysicalAssessment],
) -> PhysicalAssessment:
    return complete_structured(system, user, schema)


def _observation_citations(
    observations: list[StructuredObservation],
) -> list[EvidenceCitation]:
    return [
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


def _tool_citations(
    storm_result: ToolResult[object],
    storms: list[StormEvent],
    vessel_result: ToolResult[object],
    vessel: VesselActivity,
) -> list[EvidenceCitation]:
    citations = [
        EvidenceCitation(
            source=storm_result.source,
            reference=event.event_id,
            observed_at=datetime.combine(event.occurred_on, time.min, tzinfo=UTC),
            provenance=event.provenance,
        )
        for event in storms
    ]
    citations.append(
        EvidenceCitation(
            source=vessel_result.source,
            reference=(
                vessel_result.source_url
                or (
                    f"{vessel.site_id}:{vessel.window_start.isoformat()}"
                    f":{vessel.window_end.isoformat()}"
                )
            ),
            observed_at=datetime.combine(vessel.window_end, time.min, tzinfo=UTC),
            provenance=vessel.provenance,
        )
    )
    if not storms:
        citations.append(
            EvidenceCitation(
                source=storm_result.source,
                reference=storm_result.source_url,
                provenance=storm_result.provenance,
            )
        )
    return citations


class PhysicalAgent:
    """Assess physical-damage support from observations and two aligned tools."""

    cause = Cause.PHYSICAL

    def __init__(self, completer: PhysicalCompleter | None = None) -> None:
        self._complete = completer or _default_complete

    def assess(
        self,
        site: ReefSite,
        observations: list[StructuredObservation],
        snapshot: EvidenceSnapshot,
    ) -> CauseEvidence:
        if snapshot.site_id != site.site_id:
            raise ValueError("physical snapshot site_id must match the requested site")
        storm_result = snapshot.result(_STORM_TOOL_NAME)
        vessel_result = snapshot.result(_VESSEL_TOOL_NAME)
        storms = TypeAdapter(list[StormEvent]).validate_python(storm_result.data)
        vessel = VesselActivity.model_validate(vessel_result.data)
        if vessel.site_id != site.site_id:
            raise ValueError("vessel result site_id must match the requested site")
        site_observations = [
            observation for observation in observations if observation.site_id == site.site_id
        ]
        system = (
            "You are the physical-damage evidence investigator for a coral reef "
            "decision-support system. Assess physical damage only from the supplied "
            "field observations, storm events, and vessel facts. Do not infer an "
            "unreported grounding or storm impact, invent citations, treat support as "
            "a probability, or claim causation from proximity alone. Return only the "
            "requested structured fields."
        )
        user = (
            f"Site:\n{json.dumps(site.model_dump(mode='json'), indent=2)}\n\n"
            "Field observations:\n"
            f"{json.dumps([item.model_dump(mode='json') for item in site_observations], indent=2)}"
            "\n\n"
            "Storm tool result:\n"
            f"{json.dumps([item.model_dump(mode='json') for item in storms], indent=2)}\n\n"
            f"Vessel tool result:\n{json.dumps(vessel.model_dump(mode='json'), indent=2)}\n\n"
            "Give a 0 to 1 physical-damage support score, a 0 to 1 confidence score, one "
            "display_summary sentence under 180 characters, 1 to 3 key_findings under 110 "
            "characters each, and a full audit rationale. Every statement must name only facts "
            "present above."
        )
        assessment = self._complete(system, user, PhysicalAssessment)
        rationale_parts = [assessment.rationale]
        has_direct_damage = any(
            observation.broken_coral_observed is True for observation in site_observations
        )
        has_hazard_corroboration = bool(storms) or vessel.grounding_reports > 0
        support = assessment.support
        display_summary = assessment.display_summary
        key_findings = list(assessment.key_findings)
        if not has_direct_damage and not has_hazard_corroboration:
            support = min(support, _UNCORROBORATED_SUPPORT_CAP)
            if assessment.support > support:
                display_summary = "No corroborated physical-damage signal was supplied."
                guardrail_finding = (
                    "No broken coral, storm event, or grounding report was supplied."
                )
                key_findings = [guardrail_finding, *key_findings[:2]]
                rationale_parts.append(
                    "Support was capped at 0.20 because no broken coral, storm event, "
                    "or grounding report was supplied; vessel traffic alone is not damage."
                )
        if storm_result.provenance in (Provenance.SIMULATED, Provenance.SYNTHETIC) or (
            vessel_result.provenance in (Provenance.SIMULATED, Provenance.SYNTHETIC)
        ):
            rationale_parts.append(
                "Storm and vessel inputs are synthetic repository fixtures, not live measurements."
            )
        if storm_result.stale or vessel_result.stale:
            stale_notes = [result.note for result in (storm_result, vessel_result) if result.stale]
            rationale_parts.append(
                "Physical context is marked stale: "
                f"{', '.join(note or 'no reason supplied' for note in stale_notes)}"
            )
        if not site_observations:
            rationale_parts.append("No field observations were supplied for this site.")
        return CauseEvidence(
            cause=self.cause,
            support=support,
            confidence=assessment.confidence,
            display_summary=display_summary,
            key_findings=key_findings,
            rationale=" ".join(rationale_parts),
            citations=_observation_citations(site_observations)
            + _tool_citations(storm_result, storms, vessel_result, vessel),
            computed_at=datetime.now(UTC),
        )


def assess(
    site: ReefSite,
    observations: list[StructuredObservation],
    snapshot: EvidenceSnapshot,
    *,
    completer: PhysicalCompleter | None = None,
) -> CauseEvidence:
    """Convenience entry point for the physical-damage agent."""
    return PhysicalAgent(completer).assess(site, observations, snapshot)
