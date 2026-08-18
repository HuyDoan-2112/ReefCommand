"""NOAA Coral Reef Watch adapter.

Products: Degree Heating Weeks, Coral Bleaching HotSpot, Bleaching Alert Area,
sea-surface temperature.
Alert-level definitions follow the 5km product methodology at
coralreefwatch.noaa.gov/product/5km/.

This adapter fetches and caches. It does not interpret. Threshold logic lives in
evidence/thermal.py. The alert level here is CRW's own Bleaching Alert Area
designation, read straight from the product rather than recomputed, so this
module never turns numbers into a judgment.

Every value goes through the local cache: a live ERDDAP call under a short
timeout, automatic fallback to the cached snapshot, and no live call at all when
force_cache is set. Run scripts/prefetch_external_data.py with network access to
populate the cache before a demo. A value served from disk is labeled cache, so
the team can always answer "is this live right now".
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import httpx
from pydantic import BaseModel

from reefcommand.config import CACHE_DIR, Settings, get_settings
from reefcommand.domain.enums import AlertLevel, Provenance
from reefcommand.domain.provenance import ProvenanceMetadata
from reefcommand.ingestion._geo import site_coordinates
from reefcommand.ingestion.cache import CacheError, fetch_with_fallback, read

# Combined CRW griddap dataset carrying all four products in one request. A
# historical replay window may need the archival CoralTemp dataset id instead, so
# the endpoint lives in one place rather than being scattered through the code.
ERDDAP_CSV_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.csv"
SOURCE_URL = "https://coralreefwatch.noaa.gov/product/5km/"

_VARIABLES = ("CRW_SST", "CRW_HOTSPOT", "CRW_DHW", "CRW_BAA")
_BAA_TO_ALERT = {
    0: AlertLevel.NO_STRESS,
    1: AlertLevel.WATCH,
    2: AlertLevel.WARNING,
    3: AlertLevel.ALERT_LEVEL_1,
    4: AlertLevel.ALERT_LEVEL_2,
}


class CrwObservation(BaseModel):
    """One site, one date, as reported by Coral Reef Watch."""

    site_id: str
    observed_on: date
    sst_c: float
    hotspot_c: float
    degree_heating_weeks: float
    alert_level: AlertLevel
    provenance: Provenance
    provenance_metadata: ProvenanceMetadata | None = None


def _build_url(lat: float, lon: float, start: date, end: date) -> str:
    selector = f"[({start.isoformat()}):1:({end.isoformat()})][({lat})][({lon})]"
    query = ",".join(f"{name}{selector}" for name in _VARIABLES)
    return f"{ERDDAP_CSV_URL}?{query}"


def _parse_csv(text: str, site_id: str) -> list[CrwObservation]:
    """Parse an ERDDAP griddap CSV into observations.

    ERDDAP returns a header row, then a units row, then the data. Rows with a
    missing pixel, for example under cloud cover, come back as NaN and are
    skipped rather than invented as a zero.
    """
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 3:
        return []
    column = {name: index for index, name in enumerate(rows[0])}
    observations: list[CrwObservation] = []
    for row in rows[2:]:
        if not row:
            continue
        values = {name: row[column[name]] for name in ("time", *_VARIABLES)}
        if any(value == "" or value.upper() == "NAN" for value in values.values()):
            continue
        observations.append(
            CrwObservation(
                site_id=site_id,
                observed_on=date.fromisoformat(values["time"][:10]),
                sst_c=float(values["CRW_SST"]),
                hotspot_c=float(values["CRW_HOTSPOT"]),
                degree_heating_weeks=float(values["CRW_DHW"]),
                alert_level=_BAA_TO_ALERT[int(float(values["CRW_BAA"]))],
                provenance=Provenance.LIVE,
            )
        )
    return observations


def fetch_site_series(
    site_id: str,
    start: date,
    end: date,
    *,
    settings: Settings | None = None,
    directory: Path = CACHE_DIR,
) -> list[CrwObservation]:
    """Return the CRW series for one site over a date range.

    Served from a live ERDDAP call when possible, otherwise from the cached
    snapshot, and never from a live call when force_cache is set. Every returned
    observation carries the provenance it was actually served with.
    """
    settings = settings or get_settings()
    lat, lon = site_coordinates(site_id)

    def _live() -> list[CrwObservation]:
        response = httpx.get(
            _build_url(lat, lon, start, end),
            timeout=settings.external_timeout_seconds,
        )
        response.raise_for_status()
        return _parse_csv(response.text, site_id)

    key = f"noaa_crw:{site_id}:{start.isoformat()}:{end.isoformat()}"
    observations, provenance = fetch_with_fallback(
        key=key,
        live=_live,
        to_payload=lambda series: {"observations": [o.model_dump(mode="json") for o in series]},
        from_payload=lambda raw: [CrwObservation.model_validate(o) for o in raw["observations"]],
        timeout_seconds=settings.external_timeout_seconds,
        source_url=SOURCE_URL,
        directory=directory,
        settings=settings,
    )
    cache_entry = read(key, directory)
    if cache_entry is None:
        raise CacheError(f"cache entry disappeared after fetching {key!r}")
    provenance_metadata = ProvenanceMetadata(
        kind=provenance,
        source="NOAA Coral Reef Watch 5km",
        source_url=cache_entry.source_url or SOURCE_URL,
        fetched_at=cache_entry.fetched_at,
        note=(
            "Served from the local snapshot cache."
            if provenance is Provenance.CACHE
            else "Retrieved from the NOAA ERDDAP endpoint."
        ),
    )
    return [
        observation.model_copy(
            update={"provenance": provenance, "provenance_metadata": provenance_metadata}
        )
        for observation in observations
    ]


def prefetch_study_area(
    site_ids: list[str],
    start: date,
    end: date,
    *,
    settings: Settings | None = None,
    directory: Path = CACHE_DIR,
) -> int:
    """Cache the full replay window for the study area. Returns records written."""
    return sum(
        len(fetch_site_series(site_id, start, end, settings=settings, directory=directory))
        for site_id in site_ids
    )
