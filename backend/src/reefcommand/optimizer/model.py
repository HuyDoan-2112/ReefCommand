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

from pydantic import BaseModel

from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.resources import ResourceScenario
from reefcommand.domain.site import SiteScores


class AllocationProblem(BaseModel):
    """A fully specified allocation instance."""

    candidates: list[EligibleAction]
    scenario: ResourceScenario
    scores: dict[str, SiteScores]


def build_problem(
    approved: list[EligibleAction],
    scenario: ResourceScenario,
    scores: list[SiteScores],
) -> AllocationProblem:
    """Assemble the allocation instance."""
    raise NotImplementedError
