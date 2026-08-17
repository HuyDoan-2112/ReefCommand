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
from reefcommand.domain.intervention import EligibleAction


class BusinessRuleError(ValueError):
    """Raised when a structurally valid decision breaks a pipeline rule."""


def validate(
    decision: CoordinatorDecision,
    site_id: str,
    eligible: list[EligibleAction],
) -> CoordinatorDecision:
    """Return the decision unchanged, or raise BusinessRuleError."""
    raise NotImplementedError
