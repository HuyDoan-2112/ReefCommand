"""Versioned fixture and provenance contracts.

Persisted demo data is never allowed to rely on an implied origin.
Every fixture record carries structured provenance that distinguishes real
external data from simulated operational scenarios and synthetic signals.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from reefcommand.domain.enums import Provenance

EXTERNAL_PROVENANCE = frozenset({Provenance.LIVE, Provenance.CACHE})
DEMO_PROVENANCE = frozenset({Provenance.SIMULATED, Provenance.SYNTHETIC})


class ProvenanceMetadata(BaseModel):
    """Structured origin metadata for one value or coherent record.

    `fetched_at` records when an external value was retrieved.
    `observed_at` records when the source says the condition occurred.
    They are deliberately separate because snapshot age and observation age are
    different facts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Provenance
    source: str = Field(min_length=1, description="Human-readable source or fixture author.")
    source_url: str | None = Field(default=None, min_length=1)
    observed_at: date | AwareDatetime | None = None
    fetched_at: AwareDatetime | None = None
    note: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_honest_metadata(self) -> ProvenanceMetadata:
        """Require the metadata needed to interpret each provenance class."""
        if self.kind in EXTERNAL_PROVENANCE and self.fetched_at is None:
            raise ValueError("live and cache provenance require fetched_at")
        if self.kind in DEMO_PROVENANCE and self.note is None:
            raise ValueError("simulated and synthetic provenance require an explanatory note")
        return self

    @property
    def is_external(self) -> bool:
        """Whether this record originated from a real external source."""
        return self.kind in EXTERNAL_PROVENANCE

    @property
    def is_demo_data(self) -> bool:
        """Whether this record is simulated or synthetic demo input."""
        return self.kind in DEMO_PROVENANCE


class FixtureMetadata(BaseModel):
    """Identity and schema version for one persisted fixture document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    fixture_id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    description: str = Field(min_length=1)
    created_at: AwareDatetime


class FixtureRecord[RecordT](BaseModel):
    """One fixture record and the provenance that applies to all of its values."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: str = Field(min_length=1)
    data: RecordT
    provenance: ProvenanceMetadata


class FixtureSet[RecordT](BaseModel):
    """A versioned collection of uniquely identified, provenance-carrying records."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metadata: FixtureMetadata
    records: list[FixtureRecord[RecordT]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_persisted_records(self) -> FixtureSet[RecordT]:
        """Reject duplicate ids and persisted records that claim to be live."""
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("fixture record_id values must be unique")
        if any(record.provenance.kind is Provenance.LIVE for record in self.records):
            raise ValueError("persisted fixture records cannot claim live provenance; use cache")
        return self
