"""Contracts shared by local tools, agents, and future MCP adapters.

The contracts deliberately do not depend on a transport. A local Python tool
and a future MCP tool must produce the same validated result before an agent can
use it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from reefcommand.domain.enums import Provenance


class EvidenceWindow(BaseModel):
    """The time period a tool is allowed to inspect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: AwareDatetime
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def validate_order(self) -> EvidenceWindow:
        if self.start > self.end:
            raise ValueError("evidence window start must not be after end")
        if self.end > self.as_of:
            raise ValueError("evidence window end must not be after as_of")
        return self


class ToolResult[PayloadT](BaseModel):
    """One typed tool response with enough metadata to assess relevance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    window: EvidenceWindow
    data: PayloadT
    source: str = Field(min_length=1)
    source_url: str | None = Field(default=None, min_length=1)
    provenance: Provenance
    observed_from: AwareDatetime | None = None
    observed_until: AwareDatetime | None = None
    fetched_at: AwareDatetime | None = None
    stale: bool = False
    note: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_metadata(self) -> ToolResult[PayloadT]:
        if self.observed_from and self.observed_until and self.observed_from > self.observed_until:
            raise ValueError("observed_from must not be after observed_until")
        if self.provenance in (Provenance.LIVE, Provenance.CACHE) and self.fetched_at is None:
            raise ValueError("live and cache tool results require fetched_at")
        if self.provenance in (Provenance.SIMULATED, Provenance.SYNTHETIC) and self.note is None:
            raise ValueError("simulated and synthetic tool results require a note")
        if self.stale and self.note is None:
            raise ValueError("stale tool results require a note")
        return self


class EvidenceTool[PayloadT](Protocol):
    """Transport-independent interface implemented by a site evidence tool."""

    tool_name: str

    def read(self, site_id: str, window: EvidenceWindow) -> ToolResult[PayloadT]:
        """Return validated data for exactly one site and time window."""
        ...


class EvidenceSnapshot(BaseModel):
    """Immutable, time-aligned inputs shared by all investigators."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    as_of: AwareDatetime
    captured_at: AwareDatetime
    results: Sequence[ToolResult[object]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_alignment(self) -> EvidenceSnapshot:
        for result in self.results:
            if result.site_id != self.site_id:
                raise ValueError("all tool results in a snapshot must use the snapshot site_id")
            if result.window.as_of != self.as_of:
                raise ValueError("all tool results in a snapshot must use the snapshot as_of")
        return self

    @property
    def has_stale_data(self) -> bool:
        """Whether any source was outside its configured freshness target."""
        return any(result.stale for result in self.results)

    def result(self, tool_name: str) -> ToolResult[object]:
        """Return one tool result and reject accidental duplicate tool names."""
        matches = [result for result in self.results if result.tool_name == tool_name]
        if len(matches) != 1:
            raise KeyError(f"expected exactly one result for tool {tool_name!r}")
        return matches[0]
