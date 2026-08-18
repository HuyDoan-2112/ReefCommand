"""DATA-07: the NOAA Coral Reef Watch adapter fetches, caches, and stays offline.

The live path is mocked with respx so no real ERDDAP call is made. The tests pin
that a CSV response parses correctly, that a fetch writes the cache, and that
forced-cache mode serves the cached value without touching the network.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import respx
from httpx import Response

from reefcommand.config import Settings
from reefcommand.domain.enums import AlertLevel, Provenance
from reefcommand.ingestion import noaa_crw

START = date(2023, 8, 8)
END = date(2023, 8, 10)
LIVE = Settings(force_cache=False)
FORCED = Settings(force_cache=True)

# ERDDAP griddap CSV: header row, units row, then data. The third data row is a
# missing pixel (NaN) and must be skipped rather than read as a zero.
ERDDAP_CSV = (
    "time,latitude,longitude,CRW_SST,CRW_HOTSPOT,CRW_DHW,CRW_BAA\n"
    "UTC,degrees_north,degrees_east,degree_C,degree_C,degree_Celsius_week,\n"
    "2023-08-08T12:00:00Z,24.9125,-80.6125,31.2,1.8,15.6,4\n"
    "2023-08-09T12:00:00Z,24.9125,-80.6125,31.0,1.6,15.8,4\n"
    "2023-08-10T12:00:00Z,24.9125,-80.6125,NaN,NaN,NaN,NaN\n"
)


@respx.mock
def test_fetch_site_series_parses_and_labels_live(tmp_path: Path) -> None:
    respx.get(url__startswith=noaa_crw.ERDDAP_CSV_URL).mock(
        return_value=Response(200, text=ERDDAP_CSV)
    )

    series = noaa_crw.fetch_site_series(
        "cheeca_rocks", START, END, settings=LIVE, directory=tmp_path
    )

    assert len(series) == 2  # the NaN row is skipped
    first = series[0]
    assert first.site_id == "cheeca_rocks"
    assert first.observed_on == date(2023, 8, 8)
    assert first.degree_heating_weeks == 15.6
    assert first.sst_c == 31.2
    assert first.alert_level is AlertLevel.ALERT_LEVEL_2
    assert first.provenance is Provenance.LIVE


@respx.mock
def test_forced_cache_serves_without_network(tmp_path: Path) -> None:
    route = respx.get(url__startswith=noaa_crw.ERDDAP_CSV_URL).mock(
        return_value=Response(200, text=ERDDAP_CSV)
    )

    live = noaa_crw.fetch_site_series("cheeca_rocks", START, END, settings=LIVE, directory=tmp_path)
    assert route.call_count == 1

    cached = noaa_crw.fetch_site_series(
        "cheeca_rocks", START, END, settings=FORCED, directory=tmp_path
    )
    assert route.call_count == 1  # no new network call was made
    assert [o.provenance for o in cached] == [Provenance.CACHE] * len(cached)
    assert cached[0].degree_heating_weeks == live[0].degree_heating_weeks


@respx.mock
def test_prefetch_study_area_populates_the_cache(tmp_path: Path) -> None:
    respx.get(url__startswith=noaa_crw.ERDDAP_CSV_URL).mock(
        return_value=Response(200, text=ERDDAP_CSV)
    )

    written = noaa_crw.prefetch_study_area(
        ["cheeca_rocks", "sombrero"], START, END, settings=LIVE, directory=tmp_path
    )

    assert written == 4  # two sites, two observations each
    assert list(tmp_path.glob("*.json"))  # cache files exist on disk


def test_unknown_site_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown site_id"):
        noaa_crw.fetch_site_series("atlantis", START, END, settings=LIVE, directory=tmp_path)


def test_baa_maps_to_the_alert_level() -> None:
    parsed = noaa_crw._parse_csv(
        "time,latitude,longitude,CRW_SST,CRW_HOTSPOT,CRW_DHW,CRW_BAA\n"
        "UTC,degrees_north,degrees_east,degree_C,degree_C,degree_Celsius_week,\n"
        "2023-07-01T12:00:00Z,24.6,-81.1,29.0,0.0,0.0,0\n"
        "2023-07-02T12:00:00Z,24.6,-81.1,30.0,1.0,4.0,3\n",
        "sombrero",
    )
    assert [o.alert_level for o in parsed] == [AlertLevel.NO_STRESS, AlertLevel.ALERT_LEVEL_1]
