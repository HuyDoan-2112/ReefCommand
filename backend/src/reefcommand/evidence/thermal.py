"""Thermal-stress investigator. Deterministic.

Read NOAA DHW, HotSpot, and outlook data, apply the documented thresholds, and
compute structured evidence.

Do not use an LLM here.
Comparing numeric thresholds is not a task that needs one, and keeping this
module deterministic is what makes the NOAA IoU check in docs/evaluation.md a
meaningful pipeline-correctness test.

The module output evaluated against NOAA Bleaching Alert Area is this module's
output alone, before fusion.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from math import isfinite
from pathlib import Path

from reefcommand.config import CACHE_DIR, Settings, get_settings
from reefcommand.domain.enums import AlertLevel, Cause
from reefcommand.domain.evidence import CauseEvidence, EvidenceCitation
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite
from reefcommand.ingestion.noaa_crw import CrwObservation, SOURCE_URL, fetch_site_series

cause: Cause = Cause.THERMAL

# NOAA Coral Reef Watch alert thresholds, in degree C-weeks.
# See coralreefwatch.noaa.gov/product/5km/.
DHW_ALERT_LEVEL_1 = 4.0
DHW_ALERT_LEVEL_2 = 8.0
HOTSPOT_BLEACHING_THRESHOLD_C = 1.0
# Fixed input-quality assumption for a valid NOAA reading; not a calibrated probability.
THERMAL_INPUT_CONFIDENCE = 0.9

# This is an ordinal prototype mapping, not a calibrated probability.
_SUPPORT_BY_ALERT_LEVEL = {
    AlertLevel.NO_STRESS: 0.0,
    AlertLevel.WATCH: 0.25,
    AlertLevel.WARNING: 0.5,
    AlertLevel.ALERT_LEVEL_1: 0.75,
    AlertLevel.ALERT_LEVEL_2: 1.0,
}


def _observed_at(observed_on: date) -> datetime:
    """Represent a CRW date as an unambiguous citation timestamp."""
    return datetime.combine(observed_on, time.min, tzinfo=UTC)


def _no_data_evidence(*, computed_at: datetime, rationale: str) -> CauseEvidence:
    return CauseEvidence(
        cause=cause,
        support=0.0,
        confidence=0.0,
        rationale=rationale,
        computed_at=computed_at,
    )


def _strongest_reading(series: Sequence[CrwObservation]) -> CrwObservation:
    """Choose the highest CRW alert, then the strongest numeric reading."""
    rank = {level: index for index, level in enumerate(AlertLevel)}
    return max(
        series,
        key=lambda reading: (
            rank[alert_level_from_dhw(reading.degree_heating_weeks, reading.hotspot_c)],
            reading.degree_heating_weeks,
            reading.hotspot_c,
            reading.observed_on,
        ),
    )


def _citation(reading: CrwObservation) -> EvidenceCitation:
    metadata = reading.provenance_metadata
    return EvidenceCitation(
        source=metadata.source if metadata else "NOAA Coral Reef Watch 5km",
        reference=metadata.source_url if metadata and metadata.source_url else SOURCE_URL,
        observed_at=_observed_at(reading.observed_on),
        provenance=reading.provenance,
    )


def alert_level_from_dhw(dhw: float, hotspot_c: float) -> AlertLevel:
    """Map DHW and HotSpot to a NOAA alert level using the documented rules."""
    if not isfinite(dhw) or not isfinite(hotspot_c):
        raise ValueError("DHW and HotSpot must be finite numbers")

    if hotspot_c <= 0.0:
        return AlertLevel.NO_STRESS
    if hotspot_c < HOTSPOT_BLEACHING_THRESHOLD_C:
        return AlertLevel.WATCH
    if dhw <= 0.0:
        return AlertLevel.NO_STRESS
    if dhw < DHW_ALERT_LEVEL_1:
        return AlertLevel.WARNING
    if dhw < DHW_ALERT_LEVEL_2:
        return AlertLevel.ALERT_LEVEL_1
    return AlertLevel.ALERT_LEVEL_2


def assess(
    site: ReefSite,
    observations: list[StructuredObservation],
    *,
    crw_series: Sequence[CrwObservation] | None = None,
    settings: Settings | None = None,
    directory: Path = CACHE_DIR,
) -> CauseEvidence:
    """Compute thermal support deterministically from NOAA CRW products.

    When a CRW series is not injected, the field-observation dates define the
    cached NOAA request window. Injecting a series keeps orchestration and tests
    deterministic without duplicating the NOAA adapter's cache behavior.
    """
    computed_at = datetime.now(UTC)
    site_observations = [
        observation for observation in observations if observation.site_id == site.site_id
    ]

    if crw_series is None:
        if not site_observations:
            return _no_data_evidence(
                computed_at=computed_at,
                rationale="No field-observation window was available for NOAA thermal data.",
            )
        start = min(observation.observed_at.date() for observation in site_observations)
        end = max(observation.observed_at.date() for observation in site_observations)
        crw_series = fetch_site_series(
            site.site_id,
            start,
            end,
            settings=settings or get_settings(),
            directory=directory,
        )

    series = [reading for reading in crw_series if reading.site_id == site.site_id]
    if not series:
        return _no_data_evidence(
            computed_at=computed_at,
            rationale="No NOAA Coral Reef Watch readings were available for this site and window.",
        )

    reading = _strongest_reading(series)
    alert_level = alert_level_from_dhw(reading.degree_heating_weeks, reading.hotspot_c)
    support = _SUPPORT_BY_ALERT_LEVEL[alert_level]
    provenance_label = reading.provenance.value
    alert_label = alert_level.value.replace("_", " ").title()
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=THERMAL_INPUT_CONFIDENCE,
        rationale=(
            f"DHW {reading.degree_heating_weeks:.1f} and HotSpot {reading.hotspot_c:.1f} C "
            f"at {alert_label} across {len(series)} NOAA CRW reading(s); "
            f"source served from {provenance_label}."
        ),
        citations=[_citation(reading)],
        computed_at=computed_at,
    )
