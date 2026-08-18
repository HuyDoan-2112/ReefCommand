"""Local rainfall and turbidity evidence tool."""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.ingestion.rainfall import RainfallSignal, fetch_recent_rainfall
from reefcommand.tools.contracts import EvidenceTool, EvidenceWindow, ToolResult


class RainfallTool(EvidenceTool[RainfallSignal]):
    """Read a deterministic rainfall signal for one aligned evidence window."""

    tool_name = "rainfall"

    def read(self, site_id: str, window: EvidenceWindow) -> ToolResult[RainfallSignal]:
        days = (window.end.date() - window.start.date()).days + 1
        signal = fetch_recent_rainfall(site_id, days, end=window.end.date())
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
