"""Deterministic NOAA thermal evidence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import AlertLevel, Cause, Provenance
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.provenance import FixtureSet, ProvenanceMetadata
from reefcommand.domain.site import ReefSite
from reefcommand.evidence import thermal
from reefcommand.ingestion.noaa_crw import CrwObservation

SITES_FILE = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"


@pytest.fixture(scope="module")
def site() -> ReefSite:
    fixture = FixtureSet[ReefSite].model_validate(
        yaml.safe_load(SITES_FILE.read_text(encoding="utf-8"))
    )
    return fixture.records[0].data


def _field_observation(site_id: str, observed_at: datetime) -> StructuredObservation:
    return StructuredObservation(
        report_id="thermal-test-report",
        site_id=site_id,
        observed_at=observed_at,
    )


def _crw_reading(
    site_id: str,
    observed_on: date,
    *,
    dhw: float,
    hotspot_c: float,
) -> CrwObservation:
    return CrwObservation(
        site_id=site_id,
        observed_on=observed_on,
        sst_c=30.0,
        hotspot_c=hotspot_c,
        degree_heating_weeks=dhw,
        alert_level=thermal.alert_level_from_dhw(dhw, hotspot_c),
        provenance=Provenance.CACHE,
        provenance_metadata=ProvenanceMetadata(
            kind=Provenance.CACHE,
            source="NOAA Coral Reef Watch 5km",
            source_url="https://coralreefwatch.noaa.gov/product/5km/",
            observed_at=observed_on,
            fetched_at=datetime(2026, 8, 18, tzinfo=UTC),
        ),
    )


@pytest.mark.parametrize(
    ("dhw", "hotspot_c", "expected"),
    [
        (0.0, 0.0, AlertLevel.NO_STRESS),
        (20.0, 0.0, AlertLevel.NO_STRESS),
        (0.0, 0.5, AlertLevel.WATCH),
        (3.99, 1.0, AlertLevel.WARNING),
        (4.0, 1.0, AlertLevel.ALERT_LEVEL_1),
        (7.99, 1.2, AlertLevel.ALERT_LEVEL_1),
        (8.0, 1.0, AlertLevel.ALERT_LEVEL_2),
    ],
)
def test_alert_level_matches_noaa_thresholds(
    dhw: float,
    hotspot_c: float,
    expected: AlertLevel,
) -> None:
    assert thermal.alert_level_from_dhw(dhw, hotspot_c) is expected


def test_alert_level_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        thermal.alert_level_from_dhw(float("nan"), 1.0)


def test_assess_uses_strongest_reading_and_preserves_provenance(site: ReefSite) -> None:
    series = [
        _crw_reading(site.site_id, date(2023, 8, 8), dhw=3.0, hotspot_c=1.2),
        _crw_reading(site.site_id, date(2023, 8, 9), dhw=4.0, hotspot_c=1.4),
    ]

    evidence = thermal.assess(
        site,
        [_field_observation(site.site_id, datetime(2023, 8, 8, 12, tzinfo=UTC))],
        crw_series=series,
    )

    assert evidence.cause is Cause.THERMAL
    assert evidence.support == pytest.approx(0.75)
    assert evidence.confidence == pytest.approx(0.9)
    assert "DHW 4.0" in evidence.display_summary
    assert 1 <= len(evidence.key_findings) <= 3
    assert len(evidence.citations) == 1
    assert evidence.citations[0].provenance is Provenance.CACHE
    assert "Alert Level 1" in evidence.rationale


def test_assess_fetches_crw_for_field_observation_window(
    site: ReefSite, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, date, date]] = []

    def fake_fetch(site_id: str, start: date, end: date, **_: object) -> list[CrwObservation]:
        calls.append((site_id, start, end))
        return [_crw_reading(site_id, end, dhw=8.0, hotspot_c=1.0)]

    monkeypatch.setattr(thermal, "fetch_site_series", fake_fetch)
    evidence = thermal.assess(
        site,
        [
            _field_observation(site.site_id, datetime(2023, 8, 8, tzinfo=UTC)),
            _field_observation(site.site_id, datetime(2023, 8, 10, tzinfo=UTC)),
        ],
    )

    assert calls == [(site.site_id, date(2023, 8, 8), date(2023, 8, 10))]
    assert evidence.support == pytest.approx(1.0)


def test_assess_returns_no_support_without_a_crw_window(site: ReefSite) -> None:
    evidence = thermal.assess(site, [])

    assert evidence.support == 0.0
    assert evidence.confidence == 0.0
    assert evidence.display_summary == (
        "No thermal reading is available for this site and time window."
    )
    assert evidence.key_findings == ["No NOAA CRW reading was available"]
    assert evidence.citations == []
