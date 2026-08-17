"""Reef site models.

Study area for the prototype: the seven Florida Keys sites associated with
NOAA Mission: Iconic Reefs.

NOAA confirms these sites are ecologically and culturally significant.
NOAA does not numerically rank them, and neither does this model.

A site's values do not share an origin. Coordinates come from codified sanctuary
boundaries, ecological measurements come from one of two monitoring programmes,
and prior restoration investment is not published anywhere and is simulated.
Each of those is therefore a nested block carrying its own ProvenanceMetadata,
rather than one record-level provenance covering values of mixed origin, which
`data/README.md` forbids.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import MonitoringProgram
from reefcommand.domain.provenance import ProvenanceMetadata


class SamplingMetadata(BaseModel):
    """How a measurement was obtained, as data rather than as prose.

    Every field here exists because a reviewer could reasonably disagree with the
    choice it records. Sample size and spread are first-class so that downstream
    consumers can see how thin a measurement is, without the model imposing a
    confidence weight of its own.
    """

    model_config = ConfigDict(frozen=True)

    program: MonitoringProgram
    sampling_design: str = Field(
        description="How the programme samples, in one phrase. "
        "Not interchangeable between programmes."
    )
    reference_years: list[int] = Field(min_length=1)
    sample_n: int = Field(ge=1, description="Number of stations or sample units pooled.")
    sample_unit: str = Field(description="What one unit of sample_n is: station, or sample unit.")
    sample_sd_pct: float | None = Field(
        default=None, ge=0.0, description="Standard deviation of cover across the pooled units."
    )
    matching_method: str = Field(
        description="How this site was matched to the source data, "
        "so a reviewer can disagree with it."
    )
    matching_distance_km: float = Field(
        ge=0.0, description="Zero when the site is named in the source data."
    )
    habitat_types: list[str] = Field(min_length=1)
    richness_definition: str = Field(
        description="Neither programme publishes a richness field. "
        "This states how ours was counted."
    )
    includes_millepora: bool = Field(
        description="CREMP cover includes Millepora, a hydrocoral. NCRMP figures here exclude it."
    )
    station_ids: list[str] = Field(default_factory=list)


class SiteLocation(BaseModel):
    """A point convention applied to an area, with the convention recorded."""

    model_config = ConfigDict(frozen=True)

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    location_basis: str = Field(
        description="The convention used to reduce an area to a point. Not a survey position."
    )
    zone_name_in_source: str | None = None
    zone_span_km: float | None = Field(default=None, ge=0.0)
    provenance: ProvenanceMetadata


class EcologicalMeasurements(BaseModel):
    model_config = ConfigDict(frozen=True)

    coral_cover_pct: float = Field(ge=0.0, le=100.0)
    species_richness: int = Field(ge=0)
    sampling: SamplingMetadata
    provenance: ProvenanceMetadata


class RestorationInvestment(BaseModel):
    """Prior management commitment. Feeds strategic_value only.

    No public dataset publishes per-site restoration spend, so every value shipped
    with the prototype is simulated and its provenance says so.
    """

    model_config = ConfigDict(frozen=True)

    value: float = Field(ge=0.0, le=1.0)
    provenance: ProvenanceMetadata


class ReefSite(BaseModel):
    """A monitored reef site."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    name: str
    has_active_restoration: bool = Field(
        default=False,
        description="Whether active nursery or outplant work exists at this site. "
        "This is prior management commitment, not ecological value. "
        "Do not name specific organizations unless verified per site.",
    )
    location: SiteLocation
    measurements: EcologicalMeasurements
    restoration_investment: RestorationInvestment

    @property
    def latitude(self) -> float:
        """Convenience accessor so callers do not reach through the nested block."""
        return self.location.latitude

    @property
    def longitude(self) -> float:
        return self.location.longitude


class SiteScores(BaseModel):
    """Two scores, deliberately not blended into one.

    ecological_value = 0.6 * normalized(coral_cover) + 0.4 * normalized(species_richness)
    strategic_value  = 0.7 * ecological_value       + 0.3 * normalized(restoration_investment)

    Restoration investment is a management consideration, not an ecological one.
    Blending them into a single number quietly mixes two kinds of judgment.

    The weights are stated prototype assumptions, not scientific claims, and are
    labeled as such on the dashboard and in the pitch.
    """

    model_config = ConfigDict(frozen=True)

    site_id: str
    ecological_value: float = Field(ge=0.0, le=1.0)
    strategic_value: float = Field(ge=0.0, le=1.0)
    weights_are_prototype_assumptions: bool = Field(
        default=True,
        description="Always true. Present in the payload so the dashboard cannot forget to say so.",
    )
