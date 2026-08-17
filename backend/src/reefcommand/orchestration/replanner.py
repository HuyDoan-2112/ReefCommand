"""Re-planning.

Owns two things.

1. Deciding the minimum set of stages that must re-run for a given event, so a
   resource change does not pay for four LLM investigators that would return
   identical results.
2. Measuring the time from evidence submitted to updated plan available. That
   number is reported, see docs/evaluation.md section C, so it is measured here
   rather than estimated later.
"""

from __future__ import annotations

from reefcommand.domain.plan import ResponsePlan
from reefcommand.orchestration.events import PlanEvent


def handle(event: PlanEvent, current: ResponsePlan) -> ResponsePlan:
    """Recompute only what the event invalidated, and return the updated plan."""
    raise NotImplementedError


def is_plan_still_feasible(plan: ResponsePlan, scenario_id: str) -> bool:
    """Check the current plan against current capacity."""
    raise NotImplementedError
