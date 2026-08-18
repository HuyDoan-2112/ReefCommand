"""Storm-track and vessel-activity signals for the physical-damage investigator.

Same fallback rule as rainfall: if a live source is not integrated, return a
clearly labeled synthetic signal.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel

from reefcommand.domain.enums import Provenance
from reefcommand.ingestion._geo import site_coordinates


class StormEvent(BaseModel):
    event_id: str
    name: str | None = None
    closest_approach_km: float
    occurred_on: date
    max_wave_height_m: float | None = None
    provenance: Provenance


class VesselActivity(BaseModel):
    site_id: str
    window_start: date
    window_end: date
    transit_count: int
    anchoring_events: int
    grounding_reports: int
    provenance: Provenance


def fetch_storm_history(site_id: str, days: int) -> list[StormEvent]:
    """Return storms passing near a site within a lookback window."""
    if days < 1:
        raise ValueError("days must be at least 1")
    site_coordinates(site_id)
    site_seed = sum(ord(character) for character in site_id)
    if site_seed % 3 == 0:
        return []

    return [
        StormEvent(
            event_id=f"synthetic-storm-{site_id}",
            name="Synthetic local storm event",
            closest_approach_km=float(8 + site_seed % 18),
            occurred_on=date.today() - timedelta(days=min(days, 12)),
            max_wave_height_m=round(1.2 + (site_seed % 5) * 0.3, 1),
            provenance=Provenance.SYNTHETIC,
        )
    ]


def fetch_vessel_activity(site_id: str, days: int) -> VesselActivity:
    """Return vessel activity near a site within a lookback window."""
    if days < 1:
        raise ValueError("days must be at least 1")
    site_coordinates(site_id)
    site_seed = sum(ord(character) for character in site_id)
    window_end = date.today()
    return VesselActivity(
        site_id=site_id,
        window_start=window_end - timedelta(days=days - 1),
        window_end=window_end,
        transit_count=2 + site_seed % 7,
        anchoring_events=site_seed % 2,
        grounding_reports=1 if site_seed % 11 == 0 else 0,
        provenance=Provenance.SYNTHETIC,
    )
