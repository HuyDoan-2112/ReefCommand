"""DATA-05: the local cache must round-trip snapshots and fall back honestly.

The cache exists so the demo never depends on a live external call. These tests
pin two things: a stored snapshot round-trips with its timestamp and source
metadata intact, and `fetch_with_fallback` reports `live` or `cache` truthfully
under success, failure, timeout, and forced-cache conditions.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from reefcommand.config import Settings
from reefcommand.domain.enums import Provenance
from reefcommand.ingestion.cache import (
    CacheEntry,
    CacheError,
    CacheMissError,
    fetch_with_fallback,
    read,
    write,
)

FETCHED_AT = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
LIVE_SETTINGS = Settings(force_cache=False)
FORCED_SETTINGS = Settings(force_cache=True)


class _DhwReading(BaseModel):
    """A small typed value used to prove typed round-tripping through the cache."""

    site_id: str
    observed_on: date
    degree_heating_weeks: float


def _reading() -> _DhwReading:
    return _DhwReading(site_id="sombrero", observed_on=date(2026, 8, 16), degree_heating_weeks=8.4)


def _to_payload(reading: _DhwReading) -> dict:
    return reading.model_dump(mode="json")


def _from_payload(raw: dict) -> _DhwReading:
    return _DhwReading.model_validate(raw)


def test_write_then_read_round_trips_timestamps_and_source(tmp_path: Path) -> None:
    entry = CacheEntry(
        key="noaa_dhw:sombrero:2026-08-16",
        fetched_at=FETCHED_AT,
        source_url="https://coralreefwatch.noaa.gov/product/5km/",
        payload={"site_id": "sombrero", "degree_heating_weeks": 8.4},
    )

    write(entry, tmp_path)
    restored = read("noaa_dhw:sombrero:2026-08-16", tmp_path)

    assert restored is not None
    assert restored.key == entry.key
    assert restored.fetched_at == FETCHED_AT
    assert restored.fetched_at.tzinfo is not None
    assert restored.source_url == entry.source_url
    assert restored.payload == entry.payload


def test_read_missing_key_returns_none(tmp_path: Path) -> None:
    assert read("never_written", tmp_path) is None


def test_cache_entry_rejects_naive_fetch_time() -> None:
    with pytest.raises(ValidationError):
        CacheEntry(key="k", fetched_at=datetime(2026, 8, 17, 12, 0), payload={})


def test_cache_entry_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CacheEntry.model_validate(
            {"key": "k", "fetched_at": FETCHED_AT, "payload": {}, "unexpected": True}
        )


def test_corrupt_cache_file_fails_loudly(tmp_path: Path) -> None:
    entry = CacheEntry(key="k", fetched_at=FETCHED_AT, payload={"x": 1})
    write(entry, tmp_path)
    stored = next(tmp_path.glob("*.json"))
    stored.write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(CacheError):
        read("k", tmp_path)


def test_distinct_keys_do_not_collide(tmp_path: Path) -> None:
    first = CacheEntry(key="noaa:a", fetched_at=FETCHED_AT, payload={"which": "a"})
    second = CacheEntry(key="noaa/a", fetched_at=FETCHED_AT, payload={"which": "b"})

    write(first, tmp_path)
    write(second, tmp_path)

    assert read("noaa:a", tmp_path).payload == {"which": "a"}
    assert read("noaa/a", tmp_path).payload == {"which": "b"}


def test_fetch_with_fallback_live_success_writes_cache_and_labels_live(tmp_path: Path) -> None:
    value, provenance = fetch_with_fallback(
        key="dhw:sombrero",
        live=_reading,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=1.0,
        source_url="https://coralreefwatch.noaa.gov/product/5km/",
        directory=tmp_path,
        settings=LIVE_SETTINGS,
    )

    assert provenance is Provenance.LIVE
    assert value == _reading()

    persisted = read("dhw:sombrero", tmp_path)
    assert persisted is not None
    assert persisted.source_url == "https://coralreefwatch.noaa.gov/product/5km/"
    assert persisted.payload == _to_payload(_reading())


def test_fetch_with_fallback_falls_back_to_cache_on_error(tmp_path: Path) -> None:
    write(
        CacheEntry(key="dhw:sombrero", fetched_at=FETCHED_AT, payload=_to_payload(_reading())),
        tmp_path,
    )

    def _boom() -> _DhwReading:
        raise ConnectionError("NOAA is unreachable")

    value, provenance = fetch_with_fallback(
        key="dhw:sombrero",
        live=_boom,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=1.0,
        directory=tmp_path,
        settings=LIVE_SETTINGS,
    )

    assert provenance is Provenance.CACHE
    assert value == _reading()


def test_fetch_with_fallback_falls_back_to_cache_on_timeout(tmp_path: Path) -> None:
    write(
        CacheEntry(key="dhw:sombrero", fetched_at=FETCHED_AT, payload=_to_payload(_reading())),
        tmp_path,
    )

    def _slow() -> _DhwReading:
        time.sleep(0.5)
        return _reading()

    value, provenance = fetch_with_fallback(
        key="dhw:sombrero",
        live=_slow,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=0.05,
        directory=tmp_path,
        settings=LIVE_SETTINGS,
    )

    assert provenance is Provenance.CACHE
    assert value == _reading()


def test_force_cache_never_calls_live_and_labels_cache(tmp_path: Path) -> None:
    write(
        CacheEntry(key="dhw:sombrero", fetched_at=FETCHED_AT, payload=_to_payload(_reading())),
        tmp_path,
    )

    def _must_not_run() -> _DhwReading:
        raise AssertionError("force_cache must not attempt a live call")

    value, provenance = fetch_with_fallback(
        key="dhw:sombrero",
        live=_must_not_run,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=1.0,
        directory=tmp_path,
        settings=FORCED_SETTINGS,
    )

    assert provenance is Provenance.CACHE
    assert value == _reading()


def test_force_cache_without_snapshot_raises(tmp_path: Path) -> None:
    with pytest.raises(CacheMissError):
        fetch_with_fallback(
            key="absent",
            live=_reading,
            to_payload=_to_payload,
            from_payload=_from_payload,
            timeout_seconds=1.0,
            directory=tmp_path,
            settings=FORCED_SETTINGS,
        )


def test_live_failure_without_snapshot_raises(tmp_path: Path) -> None:
    def _boom() -> _DhwReading:
        raise ConnectionError("NOAA is unreachable")

    with pytest.raises(CacheMissError):
        fetch_with_fallback(
            key="absent",
            live=_boom,
            to_payload=_to_payload,
            from_payload=_from_payload,
            timeout_seconds=1.0,
            directory=tmp_path,
            settings=LIVE_SETTINGS,
        )


def test_typed_value_survives_a_cache_round_trip(tmp_path: Path) -> None:
    """A live value written to disk comes back as the same typed object, not a dict."""
    live_value, live_provenance = fetch_with_fallback(
        key="dhw:cheeca",
        live=_reading,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=1.0,
        directory=tmp_path,
        settings=LIVE_SETTINGS,
    )
    cached_value, cached_provenance = fetch_with_fallback(
        key="dhw:cheeca",
        live=_reading,
        to_payload=_to_payload,
        from_payload=_from_payload,
        timeout_seconds=1.0,
        directory=tmp_path,
        settings=FORCED_SETTINGS,
    )

    assert live_provenance is Provenance.LIVE
    assert cached_provenance is Provenance.CACHE
    assert isinstance(cached_value, _DhwReading)
    assert cached_value == live_value
    assert cached_value.observed_on == date(2026, 8, 16)
