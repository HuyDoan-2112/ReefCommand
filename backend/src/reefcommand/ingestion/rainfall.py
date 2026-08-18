"""Rainfall and turbidity signals for the runoff investigator.

If a real rainfall API is not wired up, this module falls back to a clearly
labeled synthetic signal.
Synthetic means synthetic in the API response, on the dashboard, and in the logs.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from reefcommand.domain.enums import Provenance


class RainfallSignal(BaseModel):
    site_id: str
    window_start: date
    window_end: date
    total_mm: float
    peak_daily_mm: float
    turbidity_index: float | None = None
    provenance: Provenance


def fetch_recent_rainfall(site_id: str, days: int) -> RainfallSignal:
    """Return the recent rainfall signal for a site."""
    raise NotImplementedError


def synthetic_rainfall(site_id: str, days: int) -> RainfallSignal:
    """Labeled synthetic fallback. Always tagged Provenance.SYNTHETIC."""
    raise NotImplementedError
