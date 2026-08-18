"""Rainfall and turbidity signals for the runoff investigator.

If a real rainfall API is not wired up, this module falls back to a clearly
labeled synthetic signal.
Synthetic means synthetic in the API response, on the dashboard, and in the logs.
"""

from __future__ import annotations

from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Provenance


class RainfallSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    site_id: str
    window_start: date
    window_end: date
    total_mm: float = Field(ge=0.0)
    peak_daily_mm: float = Field(ge=0.0)
    turbidity_index: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: Provenance
    source: str = "Synthetic rainfall and turbidity fixture"
    source_url: str | None = None
    note: str | None = None


_DEMO_RAINFALL: dict[str, tuple[float, float, float]] = {
    "carysfort": (24.0, 12.0, 0.15),
    "horseshoe": (18.0, 9.0, 0.10),
    "cheeca_rocks": (58.0, 31.0, 0.55),
    "sombrero": (12.0, 6.0, 0.08),
    "newfound_harbor": (72.0, 42.0, 0.70),
    "looe_key": (20.0, 10.0, 0.12),
    "eastern_dry_rocks": (16.0, 8.0, 0.06),
}


def _window(days: int, end: date | None) -> tuple[date, date]:
    if days < 1:
        raise ValueError("days must be at least 1")
    window_end = end or date.today()
    return window_end - timedelta(days=days - 1), window_end


def fetch_recent_rainfall(site_id: str, days: int, *, end: date | None = None) -> RainfallSignal:
    """Return a fixture-backed rainfall signal for a bounded recent window.

    A live rainfall service is intentionally not called yet. The deterministic
    fallback makes the offline pipeline reproducible and labels the result as
    synthetic in the returned model.
    """
    return synthetic_rainfall(site_id, days, end=end)


def synthetic_rainfall(site_id: str, days: int, *, end: date | None = None) -> RainfallSignal:
    """Return a clearly labeled deterministic rainfall and turbidity signal."""
    window_start, window_end = _window(days, end)
    total_mm, peak_daily_mm, turbidity_index = _DEMO_RAINFALL.get(
        site_id,
        (0.0, 0.0, 0.0),
    )
    return RainfallSignal(
        site_id=site_id,
        window_start=window_start,
        window_end=window_end,
        total_mm=total_mm,
        peak_daily_mm=peak_daily_mm,
        turbidity_index=turbidity_index,
        provenance=Provenance.SYNTHETIC,
        note=(
            "SYNTHETIC. Deterministic demo rainfall and turbidity signal; "
            "replace with a permitted local rainfall and water-quality snapshot."
        ),
    )
