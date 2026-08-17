"""Intervention knowledge base models.

The language model does not decide what treatments exist.
Every candidate action is defined here, in data, with a cited source.

Interventions in this knowledge base are source-backed, policy-eligible candidate
actions requiring manager approval.
They are not blanket "scientifically valid" prescriptions.
Eligibility means the action is grounded in a cited source and applicable to the
evidence pattern, not that it is guaranteed to work at a given site.

Shading is the clearest example of why the requirements and contraindications
fields exist: a peer-reviewed field study found no measurable shading benefit at
two coral nursery sites.
Effectiveness is context-specific.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import ActionClass, Cause


class ResourceRequirement(BaseModel):
    """What one execution of an action costs from the simulated capacity pool."""

    model_config = ConfigDict(frozen=True)

    boats: int = Field(default=0, ge=0)
    dive_teams: int = Field(default=0, ge=0)
    dive_hours: float = Field(default=0.0, ge=0.0)
    shade_units: int = Field(default=0, ge=0)
    monitoring_kits: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)


class InterventionDefinition(BaseModel):
    """One candidate action in the knowledge base."""

    model_config = ConfigDict(frozen=True)

    action_id: str
    action_class: ActionClass
    title: str
    applicable_causes: list[Cause] = Field(
        description="Which hypotheses this action responds to. May be more than one."
    )
    minimum_support: float = Field(
        ge=0.0,
        le=1.0,
        description="Support score below which this action is not eligible.",
    )
    minimum_confidence: float = Field(ge=0.0, le=1.0)
    requirements: list[str] = Field(
        description="Site or situation conditions that must hold. Checked deterministically."
    )
    contraindications: list[str] = Field(
        description="Conditions under which this action must not be offered."
    )
    resources: ResourceRequirement
    expected_compatibility: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Expected fit of this action to this evidence pattern, per the cited source. "
            "Not a guarantee of outcome."
        ),
    )
    provenance: str = Field(
        description="Citation for why this action exists in the knowledge base."
    )
    notes: str | None = None


class EligibleAction(BaseModel):
    """One knowledge-base action found eligible for a specific site right now.

    Produced by the deterministic policy engine before the Coordinator sees the case.
    The Coordinator chooses among these. It never invents one.
    """

    model_config = ConfigDict(frozen=True)

    site_id: str
    action_id: str
    action_class: ActionClass
    supporting_causes: list[Cause]
    unmet_evidence_requirements: list[str] = Field(
        default_factory=list,
        description="What is still missing. An empty list means the evidence bar is met.",
    )
    resources: ResourceRequirement
    expected_compatibility: float = Field(ge=0.0, le=1.0)
    provenance: str
    requires_manager_approval: bool = Field(
        default=True, description="Always true. The system is decision support."
    )
