"""DATA-07: the AGRRA adapter filters the curated snapshot honestly and offline.

The adapter reads a curated snapshot, never the network. These tests pin the
radius and date filtering, that record metadata is preserved, that the shipped
records are labeled synthetic, and that the adapter returns records and distances
rather than a verdict.
"""

from __future__ import annotations

from datetime import date

from reefcommand.domain.enums import Provenance
from reefcommand.ingestion import agrra_sctld

EARLY = date(2023, 1, 1)


def test_records_within_radius_are_returned_with_distances() -> None:
    nearby = agrra_sctld.find_records_near_site("cheeca_rocks", 25.0, EARLY)

    assert nearby.site_id == "cheeca_rocks"
    assert len(nearby.records) == len(nearby.distances_km)
    assert len(nearby.records) >= 1
    assert all(distance <= 25.0 for distance in nearby.distances_km)
    assert any(record.record_id.startswith("synthetic-cheeca") for record in nearby.records)


def test_far_record_is_excluded_by_the_radius() -> None:
    nearby = agrra_sctld.find_records_near_site("cheeca_rocks", 25.0, EARLY)
    assert all("far-north" not in record.record_id for record in nearby.records)


def test_since_filters_out_earlier_records() -> None:
    all_records = agrra_sctld.find_records_near_site("newfound_harbor", 25.0, EARLY)
    after = agrra_sctld.find_records_near_site("newfound_harbor", 25.0, date(2023, 9, 9))
    assert len(after.records) < len(all_records.records)
    assert all(record.submitted_on >= date(2023, 9, 9) for record in after.records)


def test_record_metadata_is_preserved() -> None:
    nearby = agrra_sctld.find_records_near_site("cheeca_rocks", 25.0, EARLY)
    record = nearby.records[0]
    assert record.submitted_on is not None
    assert record.review_status
    assert record.condition_note


def test_shipped_records_are_labeled_synthetic() -> None:
    nearby = agrra_sctld.find_records_near_site("sombrero", 25.0, EARLY)
    for record in nearby.records:
        assert record.provenance is Provenance.SYNTHETIC
        assert record.review_status == "synthetic_example"


def test_prefetch_snapshot_reports_coverage() -> None:
    sites = ["cheeca_rocks", "sombrero", "newfound_harbor", "carysfort"]
    total = agrra_sctld.prefetch_snapshot(sites, 25.0, EARLY)
    per_site = sum(len(agrra_sctld.find_records_near_site(s, 25.0, EARLY).records) for s in sites)
    assert total == per_site
    assert total >= 3
