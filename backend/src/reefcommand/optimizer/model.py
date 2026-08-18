"""The allocation problem, expressed as data.

Given a set of Coordinator-approved actions, per-site strategic value, and one
simulated resource scenario, choose the combination of actions that maximizes
total expected strategic value without violating capacity.

Constraints:

- boats available and their operational hours
- dive teams available and their hours
- inventory: shade units, monitoring kits, sampling kits
- operating budget
- daylight hours
- at most one primary action per site per window

This module builds the problem. solver.py runs it.
Keeping them apart means the problem can be unit-tested without a solver and the
baseline policy in docs/evaluation.md can be scored against the same problem
definition.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.resources import ResourceScenario
from reefcommand.domain.site import SiteScores


class AllocationProblem(BaseModel):
    """A fully specified allocation instance."""

    candidates: list[EligibleAction]
    scenario: ResourceScenario
    scores: dict[str, SiteScores]
    site_names: dict[str, str] = Field(default_factory=dict)


def build_problem(
    approved: list[EligibleAction],
    scenario: ResourceScenario,
    scores: list[SiteScores],
    site_names: dict[str, str] | None = None,
) -> AllocationProblem:
    """Assemble the allocation instance."""
    score_by_site = {score.site_id: score for score in scores}
    missing_scores = sorted({candidate.site_id for candidate in approved} - set(score_by_site))
    if missing_scores:
        raise ValueError(f"missing SiteScores for candidate sites: {missing_scores}")
    candidate_sites = {candidate.site_id for candidate in approved}
    unknown_names = set(site_names or {}) - candidate_sites
    if unknown_names:
        raise ValueError(f"site_names contains unknown candidate sites: {sorted(unknown_names)}")
    return AllocationProblem(
        candidates=approved,
        scenario=scenario,
        scores=score_by_site,
        site_names=site_names or {},
    )
