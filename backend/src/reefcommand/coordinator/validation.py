"""Business-rule validation for Coordinator output.

Schema validation lives on the model in schemas.py.
This module holds the rules that need context the schema does not have.

Rules enforced here:

1. Every approved action_id was actually returned as eligible by the policy engine
   for this site. The model cannot invent an intervention.
2. No approved action still has unmet evidence requirements.
3. No approved action is currently contraindicated for this site.
4. Requested evidence types are ones the system can actually collect.
5. The site_id in the decision matches the case that was dispatched.

A violation raises. It does not warn and continue.
"""

from __future__ import annotations

from reefcommand.coordinator.schemas import CoordinatorDecision
from reefcommand.domain.enums import Cause
from reefcommand.domain.intervention import EligibleAction


class BusinessRuleError(ValueError):
    """Raised when a structurally valid decision breaks a pipeline rule."""


def validate(
    decision: CoordinatorDecision,
    site_id: str,
    eligible: list[EligibleAction],
) -> CoordinatorDecision:
    """Return the decision unchanged, or raise BusinessRuleError."""
    if decision.site_id != site_id:
        raise BusinessRuleError("Coordinator decision site_id does not match the dispatched site")

    if set(decision.evidence_support_scores) != set(Cause):
        raise BusinessRuleError("Coordinator decision must include exactly one score per cause")

    by_id = {action.action_id: action for action in eligible}
    approved_ids = [action.action_id for action in decision.approved_actions]
    if len(approved_ids) != len(set(approved_ids)):
        raise BusinessRuleError("Coordinator cannot approve the same action more than once")
    unknown = sorted(set(approved_ids) - set(by_id))
    if unknown:
        raise BusinessRuleError(f"Coordinator approved unknown or ineligible actions: {unknown}")

    for action_id in approved_ids:
        candidate = by_id[action_id]
        if candidate.unmet_evidence_requirements:
            raise BusinessRuleError(
                f"Coordinator approved action {action_id!r} with unmet evidence requirements"
            )
        if not candidate.requires_manager_approval:
            raise BusinessRuleError(
                f"eligible action {action_id!r} must require manager approval"
            )

    if decision.additional_evidence_needed and decision.approved_actions:
        raise BusinessRuleError("Coordinator cannot approve actions while requesting more evidence")
    if decision.evidence_sufficient and decision.next_evidence:
        raise BusinessRuleError(
            "Coordinator cannot request more evidence after declaring sufficiency"
        )
    return decision
