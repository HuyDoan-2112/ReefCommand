"""Field observation models.

Field reports arrive as unstructured natural language, for example:

    "The western section looks much worse than last week. A lot of the branching
    coral is pale and there are several colonies with what looks like tissue loss."

`FieldReport` holds the raw text.
`StructuredObservation` holds what the STRUCTURE stage extracted from it.
Both are kept, so a reviewer can always see what the extractor was working from.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Provenance
from reefcommand.domain.provenance import ProvenanceMetadata


class FieldReport(BaseModel):
    """A raw observation as submitted by a diver, scientist, or restoration team."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    site_id: str
    observed_at: datetime
    observer: str
    text: str
    image_refs: list[str] = Field(default_factory=list)
    provenance: Provenance = Field(
        default=Provenance.SYNTHETIC,
        description="Demo reports are synthetic and labeled as such everywhere they appear.",
    )
    provenance_metadata: ProvenanceMetadata | None = Field(
        default=None,
        description="Record-level source and retrieval metadata from the fixture envelope.",
    )


class StructuredObservation(BaseModel):
    """Structured signals extracted from one field report.

    Every field is optional because a real report rarely mentions everything.
    Absence means "not reported", never "reported as zero".
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    site_id: str
    observed_at: datetime

    paling_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    bleaching_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    tissue_loss_observed: bool | None = None
    lesion_description: str | None = None
    affected_taxa: list[str] = Field(default_factory=list)
    spatial_progression: str | None = Field(
        default=None, description="For example 'spreading westward since last dive'."
    )
    broken_coral_observed: bool | None = None
    turbidity_note: str | None = None
    sediment_note: str | None = None
    compared_to_previous_dive: str | None = None

    extraction_notes: str | None = Field(
        default=None, description="What the extractor was unsure about. Surfaced, not swallowed."
    )
    provenance_metadata: ProvenanceMetadata | None = Field(
        default=None,
        description="Record-level source and retrieval metadata from the fixture envelope.",
    )
