"""Site value scoring.

Two scores, deliberately not blended into one:

    ecological_value = 0.6 * normalized(coral_cover)
                     + 0.4 * normalized(species_richness)

    strategic_value  = 0.7 * ecological_value
                     + 0.3 * normalized(restoration_investment)

Restoration investment reflects prior management commitment, not ecological value,
which is exactly why it lives in strategic_value and not in ecological_value.

The optimizer is wired to strategic_value.
ecological_value stays available on the dashboard as the investment-agnostic
number, for when someone asks what the reef actually needs independent of what
has already been spent there.

The weights are stated prototype assumptions, not scientific claims.
"""

from __future__ import annotations

from reefcommand.domain.site import ReefSite, SiteScores

ECOLOGICAL_WEIGHTS = {"coral_cover": 0.6, "species_richness": 0.4}
STRATEGIC_WEIGHTS = {"ecological_value": 0.7, "restoration_investment": 0.3}

WEIGHTS_DISCLAIMER = "Scoring weights are prototype assumptions, not scientific claims."


def _normalize(values: list[float]) -> list[float]:
    """Normalize values to [0, 1] relative to the scored site set.

    A constant feature has no ranking information, so it contributes zero to
    every site rather than pretending every site is a relative maximum.
    """
    if not values:
        return []

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return [0.0] * len(values)

    span = maximum - minimum
    return [(value - minimum) / span for value in values]


def score_sites(sites: list[ReefSite]) -> list[SiteScores]:
    """Compute both scores for every site, normalizing across the given set."""
    if not sites:
        return []

    coral_cover = _normalize([site.measurements.coral_cover_pct for site in sites])
    species_richness = _normalize([float(site.measurements.species_richness) for site in sites])
    restoration = _normalize(
        [site.restoration_investment.value for site in sites]
    )

    ecological_weight_cover = ECOLOGICAL_WEIGHTS["coral_cover"]
    ecological_weight_richness = ECOLOGICAL_WEIGHTS["species_richness"]
    strategic_weight_ecology = STRATEGIC_WEIGHTS["ecological_value"]
    strategic_weight_restoration = STRATEGIC_WEIGHTS["restoration_investment"]

    scores: list[SiteScores] = []
    for site, normalized_cover, normalized_richness, normalized_restoration in zip(
        sites, coral_cover, species_richness, restoration, strict=True
    ):
        ecological_value = (
            ecological_weight_cover * normalized_cover
            + ecological_weight_richness * normalized_richness
        )
        strategic_value = (
            strategic_weight_ecology * ecological_value
            + strategic_weight_restoration * normalized_restoration
        )
        scores.append(
            SiteScores(
                site_id=site.site_id,
                ecological_value=ecological_value,
                strategic_value=strategic_value,
            )
        )
    return scores
