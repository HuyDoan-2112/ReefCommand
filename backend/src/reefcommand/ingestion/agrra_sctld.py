"""AGRRA Caribbean Coral Health Watch / SCTLD Tracking Map adapter.

Source: agrra.org/coral-disease-outbreak.
Used by the disease investigator to find reviewed disease and bleaching reports
near a site.

Two rules this module exists to enforce.

1. Source metadata is preserved, not discarded after the lookup. Submission date,
   review status, and reporting organization travel with every record.
2. Geographic proximity to a reviewed record is supporting evidence, not
   confirmation. This module returns records and distances. It does not return a
   verdict, and nothing downstream may treat proximity alone as proof that a new
   field report is SCTLD.

Describe the map as AGRRA's reviewed regional tracker.
Do not assert that all Florida records are sourced specifically from FWC's Fish
and Wildlife Research Institute.

Snapshot-based by design. The tracking map is not scraped: this adapter reads a
curated snapshot that stands in for a permitted export, so it never calls the
network and forced-cache mode is satisfied trivially. Replace the shipped
snapshot with a real permitted export before making any real claim from it; the
shipped records are labeled synthetic until then.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache

import yaml
from pydantic import BaseModel

from reefcommand.config import DATA_DIR
from reefcommand.domain.enums import Provenance
from reefcommand.domain.provenance import FixtureSet, ProvenanceMetadata
from reefcommand.ingestion._geo import haversine_km, site_coordinates

SOURCE_URL = "https://www.agrra.org/coral-disease-outbreak/"
_SNAPSHOT_FILE = DATA_DIR / "agrra" / "sctld_snapshot.yaml"


class SctldRecord(BaseModel):
    """One reviewed record from the tracking map."""

    record_id: str
    latitude: float
    longitude: float
    submitted_on: date
    review_status: str
    reporting_organization: str | None = None
    condition_note: str | None = None
    provenance: Provenance
    provenance_metadata: ProvenanceMetadata | None = None


class NearbyRecords(BaseModel):
    site_id: str
    radius_km: float
    records: list[SctldRecord]
    distances_km: list[float]


@lru_cache(maxsize=1)
def _snapshot() -> tuple[SctldRecord, ...]:
    fixtures = FixtureSet[SctldRecord].model_validate(
        yaml.safe_load(_SNAPSHOT_FILE.read_text(encoding="utf-8"))
    )
    return tuple(
        record.data.model_copy(update={"provenance_metadata": record.provenance})
        for record in fixtures.records
    )


def find_records_near_site(site_id: str, radius_km: float, since: date) -> NearbyRecords:
    """Return reviewed records within a radius of a site, from the curated snapshot.

    Records are filtered by submission date and great-circle distance, and their
    source metadata is preserved. Distances are returned alongside so a caller can
    weigh proximity, but this function never decides that a record confirms SCTLD
    at the site.
    """
    lat, lon = site_coordinates(site_id)
    kept: list[SctldRecord] = []
    distances: list[float] = []
    for record in _snapshot():
        if record.submitted_on < since:
            continue
        distance = haversine_km(lat, lon, record.latitude, record.longitude)
        if distance <= radius_km:
            kept.append(record)
            distances.append(round(distance, 3))
    return NearbyRecords(site_id=site_id, radius_km=radius_km, records=kept, distances_km=distances)


def prefetch_snapshot(site_ids: list[str], radius_km: float, since: date) -> int:
    """Report how many snapshot records fall near the demo sites.

    AGRRA is snapshot-based, so the cache is the curated snapshot itself rather
    than something fetched over the network. This confirms the snapshot loads and
    returns the number of nearby records across the sites, so the prefetch step
    can report AGRRA coverage next to the NOAA cache it populated.
    """
    return sum(
        len(find_records_near_site(site_id, radius_km, since).records) for site_id in site_ids
    )
