"""Rainfall and turbidity signals for the runoff investigator.

If a real rainfall API is not wired up, this module falls back to a clearly
labeled synthetic signal.
Synthetic means synthetic in the API response, on the dashboard, and in the logs.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, Field

from reefcommand.domain.enums import Provenance
from reefcommand.ingestion._geo import site_coordinates


class RainfallSignal(BaseModel):
    site_id: str
    window_start: date
    window_end: date
    total_mm: float = Field(ge=0.0)
    peak_daily_mm: float = Field(ge=0.0)
    turbidity_index: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: Provenance


def fetch_recent_rainfall(site_id: str, days: int) -> RainfallSignal:
    """Return the recent rainfall signal for a site."""
    return synthetic_rainfall(site_id, days)


def synthetic_rainfall(site_id: str, days: int) -> RainfallSignal:
    """Labeled synthetic fallback. Always tagged Provenance.SYNTHETIC."""
    if days < 1:
        raise ValueError("days must be at least 1")
    site_coordinates(site_id)

    # Stable values make the offline demo reproducible without pretending that
    # these are observations from a weather station.
    site_seed = sum(ord(character) for character in site_id)
    total_mm = float(40 + (site_seed % 6) * 20)
    peak_daily_mm = round(total_mm * (0.35 + (site_seed % 3) * 0.05), 1)
    window_end = date.today()
    return RainfallSignal(
        site_id=site_id,
        window_start=window_end - timedelta(days=days - 1),
        window_end=window_end,
        total_mm=total_mm,
        peak_daily_mm=peak_daily_mm,
        turbidity_index=round(min(1.0, peak_daily_mm / 100.0), 3),
        provenance=Provenance.SYNTHETIC,
    )
