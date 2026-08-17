"""OR-Tools solver for the allocation problem.

Returns a ResponsePlan, including which constraints were binding, so the
dashboard can explain what resource limits caused the trade-offs rather than
just showing the result.

`solve_baseline` implements the naive comparison policy from docs/evaluation.md:
respond to whichever site reported an issue first, or has the single highest raw
DHW. It exists so the optimizer's benefit can be reported as a number against the
same problem definition and the same fixed resources.
"""

from __future__ import annotations

from reefcommand.domain.plan import ResponsePlan
from reefcommand.optimizer.model import AllocationProblem

SOLVER_TIME_LIMIT_SECONDS = 10.0


def solve(problem: AllocationProblem) -> ResponsePlan:
    """Maximize total strategic value subject to capacity constraints."""
    raise NotImplementedError


def solve_baseline(problem: AllocationProblem) -> ResponsePlan:
    """First-reported or highest-DHW-first policy, for the evaluation comparison."""
    raise NotImplementedError
