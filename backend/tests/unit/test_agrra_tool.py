"""Tests for the transport-independent AGRRA evidence tool."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from reefcommand.domain.enums import Provenance
from reefcommand.tools.agrra import AgrraSctldTool
from reefcommand.tools.contracts import EvidenceWindow


def test_read_returns_aligned_typed_result_from_snapshot() -> None:
    as_of = datetime(2023, 9, 15, 12, tzinfo=UTC)
    window = EvidenceWindow(
        as_of=as_of,
        start=as_of - timedelta(days=30),
        end=as_of,
    )

    result = AgrraSctldTool().read("cheeca_rocks", window)

    assert result.tool_name == "agrra_sctld"
    assert result.site_id == "cheeca_rocks"
    assert result.window == window
    assert result.data.site_id == "cheeca_rocks"
    assert result.data.records
    assert result.provenance is Provenance.SYNTHETIC
    assert result.note is not None
    assert result.observed_from is not None
    assert result.observed_until is not None


def test_read_marks_empty_snapshot_result_honestly() -> None:
    as_of = datetime(2023, 1, 2, 12, tzinfo=UTC)
    window = EvidenceWindow(as_of=as_of, start=as_of, end=as_of)

    result = AgrraSctldTool().read("cheeca_rocks", window)

    assert result.data.records == []
    assert result.observed_from is None
    assert result.observed_until is None
    assert result.provenance is Provenance.SYNTHETIC
