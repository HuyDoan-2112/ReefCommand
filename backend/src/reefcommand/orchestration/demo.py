"""Explicitly labeled fixture completers for the deterministic offline demo.

These functions do not call a language model. Their outputs are realistic test
fixtures used to keep the demo and automated tests reproducible. Every rationale
states that the assessment was fixture-generated.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import cast

from pydantic import TypeAdapter

from reefcommand.coordinator.agent import CoordinatorCompleter
from reefcommand.coordinator.schemas import ApprovedAction, CoordinatorOutput, EvidenceRequest
from reefcommand.domain.enums import Cause, EvidenceRequestType, Priority
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.observation import StructuredObservation
from reefcommand.evidence import disease, physical, runoff
from reefcommand.ingestion.agrra_sctld import NearbyRecords
from reefcommand.ingestion.rainfall import RainfallSignal
from reefcommand.ingestion.storm_vessel import StormEvent, VesselActivity
from reefcommand.tools import EvidenceSnapshot

_FIXTURE_LABEL = "Offline fixture-generated assessment. No LLM was called."


def disease_completer(
    observations: Sequence[StructuredObservation],
    nearby: NearbyRecords,
) -> Callable[..., disease.DiseaseAssessment]:
    site_observations = list(observations)
    has_lesion = any(
        observation.lesion_description and observation.tissue_loss_observed is True
        for observation in site_observations
    )

    def complete(
        _system: str,
        _user: str,
        _schema: type[disease.DiseaseAssessment],
    ) -> disease.DiseaseAssessment:
        if has_lesion and nearby.records:
            support, confidence = 0.82, 0.72
            rationale = "Lesion-pattern tissue loss and nearby AGRRA context are present."
        elif has_lesion:
            support, confidence = 0.62, 0.58
            rationale = "Lesion-pattern tissue loss is present without nearby AGRRA context."
        elif any(observation.tissue_loss_observed is True for observation in site_observations):
            support, confidence = 0.22, 0.45
            rationale = "Tissue loss is reported without a lesion description."
        else:
            support, confidence = 0.05, 0.42
            rationale = "No lesion pattern or disease-specific tissue loss was reported."
        return disease.DiseaseAssessment(
            support=support,
            confidence=confidence,
            rationale=f"{_FIXTURE_LABEL} {rationale}",
        )

    return complete


def runoff_completer(
    observations: Sequence[StructuredObservation],
    snapshot: EvidenceSnapshot,
) -> Callable[..., runoff.RunoffAssessment]:
    signal = cast(RainfallSignal, snapshot.result("rainfall").data)
    field_signal = any(
        observation.turbidity_note or observation.sediment_note for observation in observations
    )

    def complete(
        _system: str,
        _user: str,
        _schema: type[runoff.RunoffAssessment],
    ) -> runoff.RunoffAssessment:
        if field_signal and signal.total_mm >= 50.0:
            support, confidence = 0.82, 0.68
            rationale = "Field turbidity or sediment is paired with high recent rainfall."
        elif field_signal or signal.total_mm >= 50.0:
            support, confidence = 0.62, 0.56
            rationale = "A runoff indicator is present, but the evidence is incomplete."
        else:
            support, confidence = 0.08, 0.40
            rationale = "No strong turbidity, sediment, or recent rainfall signal was supplied."
        return runoff.RunoffAssessment(
            support=support,
            confidence=confidence,
            rationale=f"{_FIXTURE_LABEL} {rationale}",
        )

    return complete


def physical_completer(
    observations: Sequence[StructuredObservation],
    snapshot: EvidenceSnapshot,
) -> Callable[..., physical.PhysicalAssessment]:
    storms = TypeAdapter(list[StormEvent]).validate_python(snapshot.result("storm_history").data)
    vessel = cast(VesselActivity, snapshot.result("vessel_activity").data)
    broken = any(observation.broken_coral_observed is True for observation in observations)
    grounding = vessel.grounding_reports > 0
    close_storm = any(event.closest_approach_km <= 10.0 for event in storms)

    def complete(
        _system: str,
        _user: str,
        _schema: type[physical.PhysicalAssessment],
    ) -> physical.PhysicalAssessment:
        if broken and (grounding or close_storm):
            support, confidence = 0.86, 0.70
            rationale = "Broken coral is paired with a nearby storm or grounding signal."
        elif broken or grounding or close_storm:
            support, confidence = 0.62, 0.55
            rationale = "One physical-damage indicator is present without complete context."
        else:
            support, confidence = 0.05, 0.40
            rationale = "No broken coral, grounding, or close storm signal was supplied."
        return physical.PhysicalAssessment(
            support=support,
            confidence=confidence,
            rationale=f"{_FIXTURE_LABEL} {rationale}",
        )

    return complete


def _request_for(cause: Cause) -> EvidenceRequest:
    request_types = {
        Cause.THERMAL: EvidenceRequestType.REPEAT_DIVE_COMPARISON,
        Cause.DISEASE: EvidenceRequestType.CLOSE_RANGE_LESION_IMAGE,
        Cause.RUNOFF: EvidenceRequestType.TURBIDITY_READING,
        Cause.PHYSICAL: EvidenceRequestType.STRUCTURAL_DAMAGE_SURVEY,
    }
    return EvidenceRequest(
        type=request_types[cause],
        priority=1,
        rationale=f"Additional {cause.value} evidence would reduce the leading uncertainty.",
    )


def coordinator_output(
    evidence: FusedEvidence,
    candidates: Sequence[EligibleAction],
) -> CoordinatorOutput:
    actionable = [
        candidate for candidate in candidates if not candidate.unmet_evidence_requirements
    ]
    dominant = evidence.dominant_causes[0] if evidence.dominant_causes else Cause.THERMAL
    if not actionable:
        return CoordinatorOutput(
            site_id=evidence.site_id,
            evidence_sufficient=False,
            additional_evidence_needed=True,
            next_evidence=[_request_for(dominant)],
            reasoning_summary=(
                "Offline fixture Coordinator. No policy candidate has met all evidence "
                "requirements. No LLM was called."
            ),
        )
    return CoordinatorOutput(
        site_id=evidence.site_id,
        evidence_sufficient=True,
        additional_evidence_needed=False,
        approved_actions=[
            ApprovedAction(
                action_id=action.action_id,
                priority=Priority.HIGH if dominant in action.supporting_causes else Priority.MEDIUM,
                rationale=(
                    "Approved by the offline fixture Coordinator because the action is "
                    "policy-eligible and requirement-complete."
                ),
            )
            for action in actionable
        ],
        reasoning_summary=(
            "Offline fixture Coordinator approved only source-backed, requirement-complete "
            "candidates. No LLM was called."
        ),
    )


def coordinator_completer(
    evidence: FusedEvidence,
    candidates: Sequence[EligibleAction],
) -> CoordinatorCompleter:
    """Adapt the labeled fixture decision to the Coordinator protocol."""

    def complete(
        _system: str,
        _user: str,
        _schema: type[CoordinatorOutput],
    ) -> CoordinatorOutput:
        return coordinator_output(evidence, candidates)

    return cast(CoordinatorCompleter, complete)
