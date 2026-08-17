"""Storm-track and vessel-activity signals for the physical-damage investigator.

Same fallback rule as rainfall: if a live source is not integrated, return a
clearly labeled synthetic signal.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from reefcommand.domain.enums import Provenance


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
    raise NotImplementedError


def fetch_vessel_activity(site_id: str, days: int) -> VesselActivity:
    """Return vessel activity near a site within a lookback window."""
    raise NotImplementedError
