"""Storm-track and vessel-activity signals for the physical-damage investigator.

Same fallback rule as rainfall: if a live source is not integrated, return a
clearly labeled synthetic signal.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Provenance


class StormEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    name: str | None = None
    closest_approach_km: float = Field(ge=0.0)
    occurred_on: date
    max_wave_height_m: float | None = None
    provenance: Provenance


class VesselActivity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    site_id: str
    window_start: date
    window_end: date
    transit_count: int = Field(ge=0)
    anchoring_events: int = Field(ge=0)
    grounding_reports: int = Field(ge=0)
    provenance: Provenance
    source: str = "Synthetic storm and vessel fixture"
    source_url: str | None = None
    note: str | None = None


_DEMO_STORMS: dict[str, list[StormEvent]] = {
    "carysfort": [
        StormEvent(
            event_id="synthetic-carysfort-storm-2023-09-03",
            name="Synthetic September squall",
            closest_approach_km=18.0,
            occurred_on=date(2023, 9, 3),
            max_wave_height_m=1.8,
            provenance=Provenance.SYNTHETIC,
        )
    ],
    "cheeca_rocks": [],
    "horseshoe": [],
    "sombrero": [
        StormEvent(
            event_id="synthetic-sombrero-storm-2023-08-27",
            name="Synthetic August squall",
            closest_approach_km=9.0,
            occurred_on=date(2023, 8, 27),
            max_wave_height_m=2.4,
            provenance=Provenance.SYNTHETIC,
        )
    ],
    "newfound_harbor": [],
    "looe_key": [],
    "eastern_dry_rocks": [
        StormEvent(
            event_id="synthetic-eastern-dry-storm-2023-07-24",
            name="Synthetic July squall",
            closest_approach_km=6.0,
            occurred_on=date(2023, 7, 24),
            max_wave_height_m=2.1,
            provenance=Provenance.SYNTHETIC,
        )
    ],
}

_DEMO_VESSEL_ACTIVITY: dict[str, tuple[int, int, int]] = {
    "carysfort": (24, 1, 0),
    "horseshoe": (12, 0, 0),
    "cheeca_rocks": (18, 2, 0),
    "sombrero": (9, 1, 1),
    "newfound_harbor": (21, 1, 0),
    "looe_key": (15, 0, 0),
    "eastern_dry_rocks": (11, 0, 0),
}


def _window(days: int, end: date | None) -> tuple[date, date]:
    if days < 1:
        raise ValueError("days must be at least 1")
    window_end = end or date.today()
    return window_end - timedelta(days=days - 1), window_end


def fetch_storm_history(
    site_id: str,
    days: int,
    *,
    end: date | None = None,
) -> list[StormEvent]:
    """Return synthetic storms inside the requested bounded lookback window."""
    window_start, window_end = _window(days, end)
    return [
        event
        for event in _DEMO_STORMS.get(site_id, [])
        if window_start <= event.occurred_on <= window_end
    ]


def fetch_vessel_activity(
    site_id: str,
    days: int,
    *,
    end: date | None = None,
) -> VesselActivity:
    """Return a clearly labeled deterministic vessel-activity signal."""
    window_start, window_end = _window(days, end)
    transit_count, anchoring_events, grounding_reports = _DEMO_VESSEL_ACTIVITY.get(
        site_id,
        (0, 0, 0),
    )
    return VesselActivity(
        site_id=site_id,
        window_start=window_start,
        window_end=window_end,
        transit_count=transit_count,
        anchoring_events=anchoring_events,
        grounding_reports=grounding_reports,
        provenance=Provenance.SYNTHETIC,
        note=(
            "SYNTHETIC. Deterministic demo vessel-activity signal; replace with "
            "a permitted storm and vessel-activity snapshot."
        ),
    )
