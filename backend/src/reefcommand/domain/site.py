"""Reef site models.

Study area for the prototype: the seven Florida Keys sites associated with
NOAA Mission: Iconic Reefs.

NOAA confirms these sites are ecologically and culturally significant.
NOAA does not numerically rank them, and neither does this model.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Provenance


class CrempCorrespondence(BaseModel):
    """How a site's ecological measurements were matched to a CREMP station.

    CREMP monitors roughly 40 sites across the Florida Keys.
    Mission: Iconic Reefs covers seven restoration sites.
    They are not a 1:1 mapping, so the matching method is recorded rather than assumed.
    """

    model_config = ConfigDict(frozen=True)

    station_id: str
    distance_km: float = Field(ge=0.0)
    habitat_type: str
    matching_method: str = Field(
        description="How this station was selected, so a reviewer can disagree with it."
    )


class EcologicalMeasurements(BaseModel):
    model_config = ConfigDict(frozen=True)

    coral_cover_pct: float = Field(ge=0.0, le=100.0)
    species_richness: int = Field(ge=0)
    provenance: Provenance
    source_note: str = Field(
        description="Cited source, or an explicit statement that this is a labeled placeholder."
    )
    cremp: CrempCorrespondence | None = None


class ReefSite(BaseModel):
    """A monitored reef site."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    name: str
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    measurements: EcologicalMeasurements
    has_active_restoration: bool = Field(
        default=False,
        description="Whether active nursery or outplant work exists at this site. "
        "This is prior management commitment, not ecological value. "
        "Do not name specific organizations unless verified per site.",
    )
    restoration_investment: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized weight for prior restoration commitment. Feeds strategic_value only."
        ),
    )


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
