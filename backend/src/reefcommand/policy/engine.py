"""Intervention policy engine. Deterministic.

Runs before the Coordinator ever sees a case.
It answers: given this fused evidence and this site, which catalog actions are
policy-eligible and source-backed, and what evidence does each still lack.

This is what makes the Coordinator's question concrete.
The Coordinator is never asked "is the evidence sufficient" in the abstract.
It is asked against a pre-computed list of eligible actions and their evidence
requirements.

Eligibility is not a promise of effectiveness.
Shading is the standing example: a peer-reviewed field study found no measurable
benefit at two coral nursery sites, which is why requirements, contraindications,
and provenance are checked per site rather than assumed.
"""

from __future__ import annotations

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction, InterventionDefinition
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.policy import knowledge_base


def _supporting_causes(
    action: InterventionDefinition,
    evidence: FusedEvidence,
) -> list[Cause]:
    return [
        cause
        for cause in action.applicable_causes
        if evidence.support(cause) >= action.minimum_support
        and evidence.by_cause[cause].confidence >= action.minimum_confidence
    ]


def _requirement_met(
    requirement: str,
    site: ReefSite,
    evidence: FusedEvidence,
    observations: list[StructuredObservation],
) -> bool:
    lowered = requirement.lower()
    if "divable" in lowered:
        return True
    if "lesions or tissue loss" in lowered:
        return any(
            observation.tissue_loss_observed is True or observation.lesion_description
            for observation in observations
            if observation.site_id == site.site_id
        )
    if "dive is already scheduled" in lowered:
        return False
    if "turbidity or sediment" in lowered:
        field_signal = any(
            observation.turbidity_note or observation.sediment_note
            for observation in observations
            if observation.site_id == site.site_id
        )
        return field_signal or evidence.support(Cause.RUNOFF) >= 0.45
    if "defined restoration or nursery footprint" in lowered:
        return site.has_active_restoration
    return "depth and area" in lowered or "current and wave conditions" in lowered


def eligible_actions(
    site: ReefSite,
    evidence: FusedEvidence,
    observations: list[StructuredObservation] | None = None,
) -> list[EligibleAction]:
    """Return the catalog actions that are policy-eligible for this site right now.

    An action with a non-empty `unmet_evidence_requirements` is still returned.
    It is eligible in principle but not yet actionable, and the Coordinator needs
    to see it in order to know what observation would unlock it.
    """
    if evidence.site_id != site.site_id:
        raise ValueError("fused evidence site_id must match the requested site")
    observations = observations or []
    candidates: list[EligibleAction] = []
    for action in knowledge_base.retrieve():
        supporting_causes = _supporting_causes(action, evidence)
        if not supporting_causes:
            continue
        contraindications = check_contraindications(site, action.action_id)
        if contraindications:
            continue
        unmet = [
            requirement
            for requirement in action.requirements
            if not _requirement_met(requirement, site, evidence, observations)
        ]
        candidates.append(
            EligibleAction(
                site_id=site.site_id,
                action_id=action.action_id,
                action_class=action.action_class,
                supporting_causes=supporting_causes,
                unmet_evidence_requirements=unmet,
                resources=action.resources,
                expected_compatibility=action.expected_compatibility,
                provenance=action.provenance,
            )
        )
    return candidates


def check_contraindications(site: ReefSite, action_id: str) -> list[str]:
    """Return the contraindications that currently apply. Empty means none."""
    action = knowledge_base.get(action_id)
    applicable: list[str] = []
    if action.action_id == "temporary_shading" and not site.has_active_restoration:
        applicable.append("Open reef area too large for the available units to cover meaningfully")
    return applicable
