"""Contract tests for fixture and provenance honesty."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from reefcommand.domain.enums import Provenance
from reefcommand.domain.provenance import (
    FixtureMetadata,
    FixtureRecord,
    FixtureSet,
    ProvenanceMetadata,
)

FETCHED_AT = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)


def _fixture_record(
    record_id: str,
    provenance: ProvenanceMetadata,
) -> FixtureRecord[dict[str, object]]:
    return FixtureRecord(
        record_id=record_id,
        data={"site_id": "sombrero", "degree_heating_weeks": 8.4},
        provenance=provenance,
    )


def _fixture_set(
    records: list[FixtureRecord[dict[str, object]]],
) -> FixtureSet[dict[str, object]]:
    return FixtureSet(
        metadata=FixtureMetadata(
            fixture_id="noaa_demo_window",
            description="Cached NOAA observations for the demo replay window.",
            created_at=FETCHED_AT,
        ),
        records=records,
    )


@pytest.mark.parametrize("kind", [Provenance.LIVE, Provenance.CACHE])
def test_external_provenance_requires_fetch_time(kind: Provenance) -> None:
    with pytest.raises(ValidationError, match="require fetched_at"):
        ProvenanceMetadata(kind=kind, source="NOAA Coral Reef Watch")


@pytest.mark.parametrize("kind", [Provenance.SIMULATED, Provenance.SYNTHETIC])
def test_demo_provenance_requires_explanatory_note(kind: Provenance) -> None:
    with pytest.raises(ValidationError, match="require an explanatory note"):
        ProvenanceMetadata(kind=kind, source="ReefCommand demo")


def test_fetch_time_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        ProvenanceMetadata(
            kind=Provenance.CACHE,
            source="NOAA Coral Reef Watch",
            fetched_at=datetime(2026, 8, 17, 12, 0),
        )


def test_cached_record_preserves_observation_and_fetch_times() -> None:
    provenance = ProvenanceMetadata(
        kind=Provenance.CACHE,
        source="NOAA Coral Reef Watch 5km",
        source_url="https://coralreefwatch.noaa.gov/product/5km/",
        observed_at=date(2026, 8, 16),
        fetched_at=FETCHED_AT,
        note="Prefetched for the demo replay window.",
    )

    payload = provenance.model_dump(mode="json")

    assert payload["kind"] == "cache"
    assert payload["observed_at"] == "2026-08-16"
    assert payload["fetched_at"] == "2026-08-17T12:00:00Z"
    assert provenance.is_external is True
    assert provenance.is_demo_data is False


def test_synthetic_record_is_explicitly_demo_data() -> None:
    provenance = ProvenanceMetadata(
        kind=Provenance.SYNTHETIC,
        source="ReefCommand demo fixture",
        note="Synthetic rainfall signal used when no real source is integrated.",
    )

    assert provenance.is_external is False
    assert provenance.is_demo_data is True


def test_fixture_records_must_have_unique_ids() -> None:
    provenance = ProvenanceMetadata(
        kind=Provenance.CACHE,
        source="NOAA Coral Reef Watch",
        fetched_at=FETCHED_AT,
    )

    with pytest.raises(ValidationError, match="record_id values must be unique"):
        _fixture_set(
            [
                _fixture_record("sombrero_2026-08-16", provenance),
                _fixture_record("sombrero_2026-08-16", provenance),
            ]
        )


def test_persisted_fixture_cannot_claim_live_provenance() -> None:
    live = ProvenanceMetadata(
        kind=Provenance.LIVE,
        source="NOAA Coral Reef Watch",
        fetched_at=FETCHED_AT,
    )

    with pytest.raises(ValidationError, match="cannot claim live provenance"):
        _fixture_set([_fixture_record("sombrero_2026-08-16", live)])


def test_fixture_schema_is_versioned_and_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        FixtureMetadata.model_validate(
            {
                "schema_version": 2,
                "fixture_id": "future_fixture",
                "description": "Unsupported future schema.",
                "created_at": FETCHED_AT,
                "unexpected": True,
            }
        )
