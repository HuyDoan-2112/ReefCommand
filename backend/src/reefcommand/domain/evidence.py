"""Evidence models.

Naming matters here.
The field is `support`, not `probability`.
These values are not normalized to sum to 1, and the four causes are not assumed
statistically independent.

Only rename a value to a probability if a probabilistic model has actually been
calibrated against expert-labeled cases.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Cause, Provenance


class EvidenceCitation(BaseModel):
    """Where one piece of supporting evidence came from.

    Source metadata is preserved rather than discarded after a lookup.
    For AGRRA records this means submission date, review status, and the
    reporting organization survive into the dashboard.
    """

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Human-readable source name, for example 'AGRRA SCTLD map'.")
    reference: str | None = Field(default=None, description="URL or record identifier.")
    observed_at: datetime | None = None
    review_status: str | None = Field(
        default=None, description="For reviewed datasets, the record's review state."
    )
    reporting_organization: str | None = None
    provenance: Provenance = Provenance.LIVE

    def is_real(self) -> bool:
        """True when this citation is not simulated or synthetic."""
        return self.provenance in (Provenance.LIVE, Provenance.CACHE)


class CauseEvidence(BaseModel):
    """One investigator's independent assessment of one cause."""

    model_config = ConfigDict(frozen=True)

    cause: Cause
    support: float = Field(
        ge=0.0,
        le=1.0,
        description="Support score, not a probability. Not normalized against other causes.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How much the investigator trusts its own support score given input quality.",
    )
    rationale: str = Field(description="Short explanation shown on the dashboard.")
    citations: list[EvidenceCitation] = Field(default_factory=list)
    computed_at: datetime


class FusedEvidence(BaseModel):
    """Deterministic reconciliation of the four investigator outputs for one site.

    Fusion aggregates the summary.
    It does not normalize the four support scores against each other, because they
    are not competing shares of a single probability mass.
    """

    model_config = ConfigDict(frozen=True)

    site_id: str
    by_cause: dict[Cause, CauseEvidence]
    dominant_causes: list[Cause] = Field(
        description="Causes whose support clears the acting threshold. May contain more than one."
    )
    ambiguity: float = Field(
        ge=0.0,
        le=1.0,
        description="How close the leading causes are. High ambiguity is what the "
        "Coordinator resolves by requesting more evidence.",
    )
    lowest_confidence: float = Field(ge=0.0, le=1.0)
    fused_at: datetime

    def support(self, cause: Cause) -> float:
        """Support score for one cause, or 0.0 when that investigator did not report."""
        entry = self.by_cause.get(cause)
        return entry.support if entry else 0.0
