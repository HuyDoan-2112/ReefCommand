"""Local storm and vessel evidence tools."""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.domain.enums import Provenance
from reefcommand.ingestion.storm_vessel import (
    StormEvent,
    VesselActivity,
    fetch_storm_history,
    fetch_vessel_activity,
)
from reefcommand.tools.contracts import EvidenceTool, EvidenceWindow, ToolResult


class StormHistoryTool(EvidenceTool[list[StormEvent]]):
    """Read synthetic storm events in one aligned lookback window."""

    tool_name = "storm_history"

    def read(self, site_id: str, window: EvidenceWindow) -> ToolResult[list[StormEvent]]:
        days = (window.end.date() - window.start.date()).days + 1
        events = fetch_storm_history(site_id, days, end=window.end.date())
        observed_dates = [event.occurred_on for event in events]
        return ToolResult(
            tool_name=self.tool_name,
            site_id=site_id,
            window=window,
            data=events,
            source="Synthetic storm history fixture",
            provenance=events[0].provenance if events else Provenance.SYNTHETIC,
            observed_from=(
                datetime.combine(min(observed_dates), datetime.min.time(), tzinfo=UTC)
                if observed_dates
                else None
            ),
            observed_until=(
                datetime.combine(max(observed_dates), datetime.max.time(), tzinfo=UTC)
                if observed_dates
                else None
            ),
            note=(
                "SYNTHETIC. Deterministic demo storm history; replace with a permitted "
                "storm-track export."
            ),
        )


class VesselActivityTool(EvidenceTool[VesselActivity]):
    """Read synthetic vessel activity in one aligned lookback window."""

    tool_name = "vessel_activity"

    def read(self, site_id: str, window: EvidenceWindow) -> ToolResult[VesselActivity]:
        days = (window.end.date() - window.start.date()).days + 1
        signal = fetch_vessel_activity(site_id, days, end=window.end.date())
        return ToolResult(
            tool_name=self.tool_name,
            site_id=site_id,
            window=window,
            data=signal,
            source=signal.source,
            source_url=signal.source_url,
            provenance=signal.provenance,
            observed_from=datetime.combine(signal.window_start, datetime.min.time(), tzinfo=UTC),
            observed_until=datetime.combine(signal.window_end, datetime.max.time(), tzinfo=UTC),
            note=signal.note,
        )
