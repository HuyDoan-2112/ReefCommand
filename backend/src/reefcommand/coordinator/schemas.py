"""The Coordinator's structured output contract.

The Coordinator must never send free-form prose into the optimizer.
This module is that guarantee, expressed as types.

    Coordinator LLM
        |
    schema-constrained structured output   <- this module
        |
    Pydantic / JSON Schema validation      <- this module
        |
    business-rule validation               <- validation.py
        |
    Optimizer

Malformed or incomplete output fails validation instead of propagating downstream.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reefcommand.domain.enums import Cause, EvidenceRequestType, Priority


class SupportScore(BaseModel):
    """One cause's support and confidence, as received from evidence fusion.

    The Coordinator does not compute these.
    It reasons over them.
    """

    model_config = ConfigDict(frozen=True)

    support: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class EvidenceRequest(BaseModel):
    """An additional observation the Coordinator wants before acting."""

    model_config = ConfigDict(frozen=True)

    type: EvidenceRequestType
    priority: int = Field(ge=1, description="1 is most urgent.")
    rationale: str = Field(
        min_length=1, description="Which ambiguity this observation would resolve."
    )


class ApprovedAction(BaseModel):
    """An eligible action the Coordinator judges the current evidence supports acting on.

    `action_id` must be one the policy engine already marked eligible for this site.
    The Coordinator cannot invent an action, and validation.py enforces that.
    """

    model_config = ConfigDict(frozen=True)

    action_id: str = Field(min_length=1)
    priority: Priority
    rationale: str = Field(min_length=1)


class CoordinatorOutput(BaseModel):
    """Fields the LLM is allowed to decide."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    site_id: str = Field(min_length=1)
    evidence_sufficient: bool
    additional_evidence_needed: bool
    next_evidence: list[EvidenceRequest] = Field(default_factory=list)
    approved_actions: list[ApprovedAction] = Field(default_factory=list)
    reasoning_summary: str = Field(
        min_length=1, description="Shown on the dashboard. Never parsed by the optimizer."
    )

    @model_validator(mode="after")
    def check_internal_consistency(self) -> CoordinatorOutput:
        """Reject decisions that contradict themselves.

        These are schema-level invariants.
        Cross-object rules, such as "this action_id was actually eligible", live in
        validation.py because they need the policy engine's output to check.
        """
        if self.evidence_sufficient == self.additional_evidence_needed:
            raise ValueError("evidence_sufficient and additional_evidence_needed must be opposites")
        if self.additional_evidence_needed and not self.next_evidence:
            raise ValueError("additional_evidence_needed is true but next_evidence is empty")
        if self.evidence_sufficient and not self.approved_actions:
            raise ValueError("evidence_sufficient is true but no action was approved")
        priorities = [request.priority for request in self.next_evidence]
        if len(priorities) != len(set(priorities)):
            raise ValueError("next_evidence priorities must be distinct")
        return self


class CoordinatorDecision(CoordinatorOutput):
    """Validated output plus evidence scores copied from deterministic fusion."""

    evidence_support_scores: dict[Cause, SupportScore]
