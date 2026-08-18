"""Runoff and water-quality investigator. LLM plus tools.

Combines diver descriptions, recent rainfall, turbidity information, geographic
context, proximity to runoff sources, and water-quality evidence.

If a real rainfall API is not wired up, the rainfall input is a clearly labeled
synthetic signal and that label travels into the citations.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.rainfall import fetch_recent_rainfall

cause: Cause = Cause.RUNOFF
RUNOFF_LOOKBACK_DAYS = 7
RUNOFF_INPUT_CONFIDENCE = 0.55


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine turbidity and sediment reports with the rainfall signal."""
    computed_at = datetime.now(UTC)
    site_observations = [
        observation for observation in observations if observation.site_id == site.site_id
    ]
    rainfall = fetch_recent_rainfall(site.site_id, RUNOFF_LOOKBACK_DAYS)

    field_support = 0.0
    field_signals: list[str] = []
    if any(observation.turbidity_note for observation in site_observations):
        field_support += 0.25
        field_signals.append("turbidity note")
    if any(observation.sediment_note for observation in site_observations):
        field_support += 0.25
        field_signals.append("sediment note")

    rain_support = min(1.0, rainfall.total_mm / 200.0) * 0.3
    rain_support += min(1.0, rainfall.peak_daily_mm / 75.0) * 0.2
    support = min(1.0, field_support + rain_support)
    observed_at = datetime.combine(rainfall.window_end, time.min, tzinfo=UTC)
    citation = EvidenceCitation(
        source="Synthetic rainfall fallback",
        observed_at=observed_at,
        provenance=rainfall.provenance,
    )
    field_summary = ", ".join(field_signals) if field_signals else "no field turbidity or sediment note"
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=RUNOFF_INPUT_CONFIDENCE,
        rationale=(
            f"The {RUNOFF_LOOKBACK_DAYS}-day rainfall signal totals {rainfall.total_mm:.1f} mm "
            f"with a {rainfall.peak_daily_mm:.1f} mm peak; {field_summary}. "
            "Rainfall is synthetic fallback data and is not a real environmental observation."
        ),
        citations=[citation],
        computed_at=computed_at,
    )
