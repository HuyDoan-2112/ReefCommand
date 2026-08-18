"""Local AGRRA SCTLD evidence tool.

The tool is transport-independent. It reads the curated AGRRA snapshot today,
and the same `read` contract can later be exposed through an MCP adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.domain.enums import Provenance
from reefcommand.ingestion.agrra_sctld import (
    SOURCE_URL,
    NearbyRecords,
    find_records_near_site,
)
from reefcommand.tools.contracts import EvidenceTool, EvidenceWindow, ToolResult


class AgrraSctldTool(EvidenceTool[NearbyRecords]):
    """Read nearby AGRRA tracker records for one aligned evidence window."""

    tool_name = "agrra_sctld"

    def __init__(self, radius_km: float = 25.0) -> None:
        if radius_km <= 0:
            raise ValueError("radius_km must be positive")
        self.radius_km = radius_km

    def read(self, site_id: str, window: EvidenceWindow) -> ToolResult[NearbyRecords]:
        nearby = find_records_near_site(
            site_id,
            self.radius_km,
            window.start.date(),
            window.end.date(),
        )
        observed_dates = [record.submitted_on for record in nearby.records]
        observed_from = (
            datetime.combine(min(observed_dates), datetime.min.time(), tzinfo=UTC)
            if observed_dates
            else None
        )
        observed_until = (
            datetime.combine(max(observed_dates), datetime.max.time(), tzinfo=UTC)
            if observed_dates
            else None
        )
        return ToolResult(
            tool_name=self.tool_name,
            site_id=site_id,
            window=window,
            data=nearby,
            source="AGRRA reviewed regional tracker snapshot",
            source_url=SOURCE_URL,
            provenance=Provenance.SYNTHETIC,
            observed_from=observed_from,
            observed_until=observed_until,
            note=(
                "The repository snapshot contains synthetic example records. "
                "Replace it with a permitted export before making real disease claims."
            ),
        )
