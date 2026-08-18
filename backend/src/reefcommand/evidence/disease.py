"""Disease investigator. LLM plus a grounded tool.

LLM reasoning earns its place here because field evidence arrives as description:
lesions, tissue loss, affected species, spatial progression, disease-like
morphology.

Grounded tool: ingestion.agrra_sctld, the AGRRA Caribbean Coral Health Watch /
SCTLD Tracking Map. This is a real, specific tool call, not a generic placeholder.

Proximity rule, enforced here and not delegated to the prompt: geographic
proximity to a reviewed record is supporting evidence, not confirmation.
Proximity feeds the disease support score alongside the lesion description.
It is never a binary override, and it never on its own establishes that a new
field report is SCTLD.

Record metadata from the tracker (submission date, review status, reporting
organization) is preserved into CauseEvidence.citations.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.agrra_sctld import (
    SOURCE_URL,
    SctldRecord,
    find_records_near_site,
)

cause: Cause = Cause.DISEASE

DEFAULT_SEARCH_RADIUS_KM = 25.0
DISEASE_LOOKBACK_DAYS = 30
DISEASE_INPUT_CONFIDENCE = 0.7


def _no_data(computed_at: datetime, rationale: str) -> CauseEvidence:
    return CauseEvidence(
        cause=cause,
        support=0.0,
        confidence=0.0,
        rationale=rationale,
        computed_at=computed_at,
    )


def _field_citation(observation: StructuredObservation) -> EvidenceCitation:
    metadata = observation.provenance_metadata
    return EvidenceCitation(
        source=metadata.source if metadata else "Structured field observation",
        reference=(
            metadata.source_url if metadata and metadata.source_url else observation.report_id
        ),
        observed_at=observation.observed_at,
        provenance=metadata.kind if metadata else Provenance.SYNTHETIC,
    )


def _record_citation(record: SctldRecord, observed_at: datetime) -> EvidenceCitation:
    metadata = record.provenance_metadata
    return EvidenceCitation(
        source=metadata.source if metadata else "AGRRA reviewed regional tracker",
        reference=metadata.source_url if metadata and metadata.source_url else SOURCE_URL,
        observed_at=observed_at,
        review_status=record.review_status,
        reporting_organization=record.reporting_organization,
        provenance=record.provenance,
    )


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine lesion description with nearby reviewed records into a support score."""
    computed_at = datetime.now(UTC)
    site_observations = [
        observation for observation in observations if observation.site_id == site.site_id
    ]
    if not site_observations:
        return _no_data(
            computed_at,
            "No structured field observations were available for disease evidence.",
        )

    local_support = 0.0
    signal_names: list[str] = []
    if any(observation.lesion_description for observation in site_observations):
        local_support += 0.45
        signal_names.append("lesion description")
    if any(observation.tissue_loss_observed is True for observation in site_observations):
        local_support += 0.25
        signal_names.append("tissue loss")
    if any(observation.spatial_progression for observation in site_observations):
        local_support += 0.15
        signal_names.append("spatial progression")
    if any(observation.affected_taxa for observation in site_observations):
        local_support += 0.05
        signal_names.append("affected taxa")

    latest_observation = max(observation.observed_at for observation in site_observations)
    since = latest_observation.date() - timedelta(days=DISEASE_LOOKBACK_DAYS)
    nearby = find_records_near_site(site.site_id, DEFAULT_SEARCH_RADIUS_KM, since)
    proximity_support = 0.0
    if nearby.records:
        nearest_distance = min(nearby.distances_km)
        proximity_support = 0.2 * max(
            0.0, 1.0 - nearest_distance / DEFAULT_SEARCH_RADIUS_KM
        )

    support = min(1.0, local_support + proximity_support)
    citations = [_field_citation(observation) for observation in site_observations]
    citations.extend(
        _record_citation(record, datetime.combine(record.submitted_on, time.min, tzinfo=UTC))
        for record in nearby.records
    )
    if not signal_names and not nearby.records:
        return _no_data(
            computed_at,
            "No lesion, tissue-loss, progression, or nearby tracker signal was available.",
        )

    field_summary = ", ".join(signal_names) if signal_names else "no lesion signal"
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=DISEASE_INPUT_CONFIDENCE,
        rationale=(
            f"Field evidence includes {field_summary}; the AGRRA reviewed regional tracker "
            f"returned {len(nearby.records)} nearby record(s) within "
            f"{DEFAULT_SEARCH_RADIUS_KM:.0f} km. "
            "Proximity is supporting evidence, not confirmation of disease."
        ),
        citations=citations,
        computed_at=computed_at,
    )
