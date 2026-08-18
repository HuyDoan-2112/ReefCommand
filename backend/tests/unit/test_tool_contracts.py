"""Tests for transport-independent evidence tool contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from reefcommand.domain.enums import Provenance
from reefcommand.tools.contracts import EvidenceSnapshot, EvidenceWindow, ToolResult

AS_OF = datetime(2023, 9, 15, 12, tzinfo=UTC)
WINDOW = EvidenceWindow(
    as_of=AS_OF,
    start=AS_OF - timedelta(days=7),
    end=AS_OF,
)


def _result(
    tool_name: str,
    *,
    site_id: str = "cheeca_rocks",
    as_of: datetime = AS_OF,
    stale: bool = False,
    note: str | None = None,
) -> ToolResult[dict[str, str]]:
    window = EvidenceWindow(as_of=as_of, start=as_of - timedelta(days=7), end=as_of)
    return ToolResult(
        tool_name=tool_name,
        site_id=site_id,
        window=window,
        data={"status": "ok"},
        source="fixture tool",
        provenance=Provenance.SYNTHETIC,
        stale=stale,
        note=note if note is not None else "Synthetic test data.",
    )


def test_window_rejects_future_data() -> None:
    with pytest.raises(ValidationError, match="after as_of"):
        EvidenceWindow(
            as_of=AS_OF,
            start=AS_OF,
            end=AS_OF + timedelta(minutes=1),
        )


def test_snapshot_requires_one_common_site_and_as_of() -> None:
    snapshot = EvidenceSnapshot(
        snapshot_id="snapshot-20230915-cheeca",
        site_id="cheeca_rocks",
        as_of=AS_OF,
        captured_at=AS_OF + timedelta(minutes=1),
        results=[_result("agrra"), _result("rainfall")],
    )

    assert snapshot.result("agrra").data == {"status": "ok"}
    assert snapshot.has_stale_data is False


def test_snapshot_rejects_misaligned_results() -> None:
    with pytest.raises(ValidationError, match="snapshot site_id"):
        EvidenceSnapshot(
            snapshot_id="snapshot-20230915-cheeca",
            site_id="cheeca_rocks",
            as_of=AS_OF,
            captured_at=AS_OF,
            results=[_result("agrra", site_id="sombrero")],
        )


def test_stale_result_requires_explanation_and_is_visible() -> None:
    with pytest.raises(ValidationError, match="note"):
        _result("rainfall", stale=True, note="")

    snapshot = EvidenceSnapshot(
        snapshot_id="snapshot-20230915-cheeca",
        site_id="cheeca_rocks",
        as_of=AS_OF,
        captured_at=AS_OF,
        results=[_result("rainfall", stale=True, note="Cached value is 2 days old.")],
    )
    assert snapshot.has_stale_data is True
