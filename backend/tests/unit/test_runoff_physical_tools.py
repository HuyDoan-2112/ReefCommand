"""Tests for local runoff and physical-context tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from reefcommand.domain.enums import Provenance
from reefcommand.tools.rainfall import RainfallTool
from reefcommand.tools.storm_vessel import StormHistoryTool, VesselActivityTool
from reefcommand.tools.contracts import EvidenceWindow


def _window() -> EvidenceWindow:
    as_of = datetime(2023, 9, 15, 12, tzinfo=UTC)
    return EvidenceWindow(as_of=as_of, start=as_of - timedelta(days=30), end=as_of)


def test_rainfall_tool_returns_aligned_synthetic_signal() -> None:
    result = RainfallTool().read("newfound_harbor", _window())

    assert result.tool_name == "rainfall"
    assert result.data.site_id == "newfound_harbor"
    assert result.data.total_mm > 0
    assert result.provenance is Provenance.SYNTHETIC
    assert result.note is not None
    assert result.window.end.date() == result.data.window_end


def test_storm_tool_excludes_events_after_snapshot() -> None:
    result = StormHistoryTool().read("sombrero", _window())

    assert result.tool_name == "storm_history"
    assert all(event.occurred_on <= result.window.end.date() for event in result.data)
    assert result.provenance is Provenance.SYNTHETIC
    assert result.note is not None


def test_vessel_tool_preserves_window_and_synthetic_label() -> None:
    result = VesselActivityTool().read("cheeca_rocks", _window())

    assert result.tool_name == "vessel_activity"
    assert result.data.site_id == "cheeca_rocks"
    assert result.data.window_start == result.window.start.date()
    assert result.data.window_end == result.window.end.date()
    assert result.provenance is Provenance.SYNTHETIC
