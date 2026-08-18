"""Site value scoring.

The point of these tests is the separation: restoration investment must move
strategic_value and must not move ecological_value.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.site import ReefSite
from reefcommand.optimizer.scoring import score_sites

SITES_FILE = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"


@pytest.fixture(scope="module")
def sites() -> list[ReefSite]:
    fixture = FixtureSet[ReefSite].model_validate(
        yaml.safe_load(SITES_FILE.read_text(encoding="utf-8"))
    )
    return [record.data for record in fixture.records]


def _with_values(
    site: ReefSite,
    *,
    coral_cover_pct: float,
    species_richness: int,
    restoration_value: float,
) -> ReefSite:
    measurements = site.measurements.model_copy(
        update={
            "coral_cover_pct": coral_cover_pct,
            "species_richness": species_richness,
        }
    )
    restoration = site.restoration_investment.model_copy(update={"value": restoration_value})
    return site.model_copy(
        update={"measurements": measurements, "restoration_investment": restoration}
    )


def test_empty_site_set_returns_no_scores() -> None:
    assert score_sites([]) == []


def test_scores_preserve_input_order_and_site_ids(sites) -> None:
    scores = score_sites(sites)
    assert [score.site_id for score in scores] == [site.site_id for site in sites]


def test_scores_are_normalized_to_the_scored_set(sites) -> None:
    sample = [
        _with_values(sites[0], coral_cover_pct=0.0, species_richness=0, restoration_value=0.0),
        _with_values(sites[1], coral_cover_pct=100.0, species_richness=100, restoration_value=1.0),
    ]

    scores = score_sites(sample)

    assert scores[0].ecological_value == pytest.approx(0.0)
    assert scores[0].strategic_value == pytest.approx(0.0)
    assert scores[1].ecological_value == pytest.approx(1.0)
    assert scores[1].strategic_value == pytest.approx(1.0)


def test_restoration_investment_does_not_change_ecological_value(sites) -> None:
    """Two sites with identical ecology score identically on ecological_value."""
    sample = [
        _with_values(sites[0], coral_cover_pct=20.0, species_richness=10, restoration_value=0.0),
        _with_values(sites[1], coral_cover_pct=20.0, species_richness=10, restoration_value=1.0),
    ]

    scores = score_sites(sample)

    assert scores[0].ecological_value == pytest.approx(scores[1].ecological_value)
    assert scores[0].ecological_value == pytest.approx(0.0)


def test_restoration_investment_raises_strategic_value(sites) -> None:
    sample = [
        _with_values(sites[0], coral_cover_pct=20.0, species_richness=10, restoration_value=0.0),
        _with_values(sites[1], coral_cover_pct=20.0, species_richness=10, restoration_value=1.0),
    ]

    scores = score_sites(sample)

    assert scores[1].strategic_value > scores[0].strategic_value


def test_weights_disclaimer_travels_with_the_scores(sites) -> None:
    """The dashboard cannot render the numbers without the assumption label."""
    scores = score_sites(sites)
    assert scores
    assert all(score.weights_are_prototype_assumptions for score in scores)
