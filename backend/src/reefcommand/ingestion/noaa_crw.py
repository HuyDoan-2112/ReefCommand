"""NOAA Coral Reef Watch adapter.

Products: Degree Heating Weeks, Coral Bleaching HotSpot, Bleaching Alert Area,
sea-surface temperature, bleaching outlook.
Alert-level definitions follow the 5km product methodology at
coralreefwatch.noaa.gov/product/5km/.

This adapter fetches and caches.
It does not interpret.
Threshold logic lives in evidence/thermal.py.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from reefcommand.domain.enums import AlertLevel, Provenance


class CrwObservation(BaseModel):
    """One site, one date, as reported by Coral Reef Watch."""

    site_id: str
    observed_on: date
    sst_c: float
    hotspot_c: float
    degree_heating_weeks: float
    alert_level: AlertLevel
    provenance: Provenance


def fetch_site_series(site_id: str, start: date, end: date) -> list[CrwObservation]:
    """Return the CRW series for one site over a date range."""
    raise NotImplementedError


def prefetch_study_area(site_ids: list[str], start: date, end: date) -> int:
    """Cache the full replay window for the study area. Returns records written."""
    raise NotImplementedError
