"""Physical-damage investigator. LLM plus tools.

Combines reports of broken coral, storm history, wave and storm information,
vessel activity, and anchor or grounding observations.

Same synthetic-labeling rule as runoff.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.storm_vessel import fetch_storm_history, fetch_vessel_activity

cause: Cause = Cause.PHYSICAL
PHYSICAL_LOOKBACK_DAYS = 30
PHYSICAL_INPUT_CONFIDENCE = 0.55


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine breakage reports with storm and vessel history."""
    computed_at = datetime.now(UTC)
    site_observations = [
        observation for observation in observations if observation.site_id == site.site_id
    ]
    storms = fetch_storm_history(site.site_id, PHYSICAL_LOOKBACK_DAYS)
    vessels = fetch_vessel_activity(site.site_id, PHYSICAL_LOOKBACK_DAYS)

    support = 0.2 if storms else 0.0
    signals: list[str] = []
    if storms:
        signals.append(f"{len(storms)} nearby storm event(s)")
    if any(observation.broken_coral_observed is True for observation in site_observations):
        support += 0.45
        signals.append("broken-coral report")
    if vessels.anchoring_events:
        support += 0.2
        signals.append("anchoring activity")
    if vessels.grounding_reports:
        support += 0.25
        signals.append("grounding report")
    support += min(0.1, vessels.transit_count / 100.0)
    support = min(1.0, support)

    citations = [
        EvidenceCitation(
            source="Synthetic storm-history fallback",
            observed_at=datetime.combine(storm.occurred_on, time.min, tzinfo=UTC),
            provenance=storm.provenance,
        )
        for storm in storms
    ]
    citations.append(
        EvidenceCitation(
            source="Synthetic vessel-activity fallback",
            observed_at=datetime.combine(vessels.window_end, time.min, tzinfo=UTC),
            provenance=vessels.provenance,
        )
    )
    signal_summary = ", ".join(signals) if signals else "no direct physical-damage signal"
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=PHYSICAL_INPUT_CONFIDENCE,
        rationale=(
            f"The {PHYSICAL_LOOKBACK_DAYS}-day physical lookback found {signal_summary}. "
            "Storm and vessel values are synthetic fallback signals, not real activity records."
        ),
        citations=citations,
        computed_at=computed_at,
    )
