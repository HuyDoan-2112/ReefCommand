"""End-to-end pipeline for one planning window.

    OBSERVE
       |
    STRUCTURE
       |
    INVESTIGATE                       (four investigators, run in parallel)
       |
    FUSE EVIDENCE                     (deterministic)
       |
    CONSTRAIN TO POLICY-ELIGIBLE ACTIONS
       |
    REASON ABOUT UNCERTAINTY          (Coordinator: act now, or get more data)
       |
    OPTIMIZE
       |
    ACT / DISPLAY PLAN

The execution path is dynamic. When the Coordinator finds evidence insufficient,
the case loops back for another observation instead of proceeding to the
optimizer. That changing path is the reason an autonomous agent is warranted at
this one point in the system, and nowhere else.
"""

from __future__ import annotations

from reefcommand.domain.plan import ResponsePlan


def run(scenario_id: str, site_ids: list[str]) -> ResponsePlan:
    """Run the full pipeline and return a response plan."""
    raise NotImplementedError
