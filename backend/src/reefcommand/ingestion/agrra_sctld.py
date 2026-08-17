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

Do not assume the dashboard allows unrestricted automated scraping.
For the demo, use a permitted export or a manually curated snapshot.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from reefcommand.domain.enums import Provenance


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


class NearbyRecords(BaseModel):
    site_id: str
    radius_km: float
    records: list[SctldRecord]
    distances_km: list[float]


def find_records_near_site(site_id: str, radius_km: float, since: date) -> NearbyRecords:
    """Return reviewed records within a radius of a site."""
    raise NotImplementedError


def prefetch_snapshot(site_ids: list[str], radius_km: float, since: date) -> int:
    """Cache a snapshot for the demo sites. Returns records written."""
    raise NotImplementedError
