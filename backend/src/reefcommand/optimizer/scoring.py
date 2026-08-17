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


def score_sites(sites: list[ReefSite]) -> list[SiteScores]:
    """Compute both scores for every site, normalizing across the given set."""
    raise NotImplementedError
