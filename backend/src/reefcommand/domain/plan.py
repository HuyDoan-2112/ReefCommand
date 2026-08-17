"""Response plan models.

The output should read like an operations plan, not like an AI answer.

The dashboard also has to explain what evidence supported the decision, what
uncertainty remains, what resource constraints caused trade-offs, and why an
intervention was considered compatible.
Those explanations are fields on these models, not an afterthought in the UI.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import ActionClass, Priority


class Assignment(BaseModel):
    """One boat and team sent to one site to perform one action."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    site_name: str
    action_id: str
    action_class: ActionClass
    boat_id: str | None = None
    team_id: str | None = None
    priority: Priority
    estimated_hours: float = Field(ge=0.0)
    estimated_cost_usd: float = Field(ge=0.0)

    evidence_summary: str = Field(description="What evidence supported this decision.")
    remaining_uncertainty: str = Field(description="What we still do not know.")
    compatibility_rationale: str = Field(
        description="Why this action was considered compatible, with its knowledge-base provenance."
    )
    requires_manager_approval: bool = True


class DeferredSite(BaseModel):
    """A site that needed attention but did not fit within capacity."""

    model_config = ConfigDict(frozen=True)

    site_id: str
    site_name: str
    fallback_action_id: str | None = Field(
        default=None, description="For example monitoring only, when intervention was deferred."
    )
    reason: str = Field(description="The binding constraint, stated plainly.")


class ResponsePlan(BaseModel):
    """A complete allocation for one planning window."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    generated_at: datetime
    scenario_id: str
    scenario_banner: str = Field(
        description="Simulated-data banner text, carried on the plan so it cannot be dropped."
    )
    assignments: list[Assignment]
    deferred: list[DeferredSite] = Field(default_factory=list)
    total_strategic_value: float = Field(
        ge=0.0, description="Objective value achieved. Comparable against the naive baseline."
    )
    binding_constraints: list[str] = Field(
        default_factory=list,
        description="Which constraints were tight, so trade-offs are explainable.",
    )
    replan_trigger: str | None = Field(
        default=None, description="What caused this recompute, when it was not the first plan."
    )
    replan_latency_ms: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Evidence submitted to plan displayed. Reported metric, see docs/evaluation.md."
        ),
    )
