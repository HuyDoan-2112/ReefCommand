"""Shared geography helpers for the ingestion adapters.

Site coordinates come from the sites fixture, so an adapter never hard-codes a
position that could drift from the curated one. Distances use the haversine
great-circle formula, which is accurate enough at reef spacing.
"""

from __future__ import annotations

from functools import lru_cache
from math import asin, cos, radians, sin, sqrt

import yaml

from reefcommand.config import DATA_DIR

_SITES_FILE = DATA_DIR / "sites" / "iconic_reefs.yaml"
EARTH_RADIUS_KM = 6371.0088


@lru_cache(maxsize=1)
def _coordinates() -> dict[str, tuple[float, float]]:
    document = yaml.safe_load(_SITES_FILE.read_text(encoding="utf-8"))
    coordinates: dict[str, tuple[float, float]] = {}
    for record in document["records"]:
        location = record["data"]["location"]
        coordinates[record["data"]["site_id"]] = (
            float(location["latitude"]),
            float(location["longitude"]),
        )
    return coordinates


def site_coordinates(site_id: str) -> tuple[float, float]:
    """Return (latitude, longitude) for a study site, or raise for an unknown id."""
    coordinates = _coordinates().get(site_id)
    if coordinates is None:
        raise ValueError(f"unknown site_id {site_id!r}")
    return coordinates


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometers."""
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))
