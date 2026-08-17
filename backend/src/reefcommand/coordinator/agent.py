"""Coordinator agent execution.

    fused evidence + eligible actions
        |
    LLM call with a constrained output schema
        |
    CoordinatorDecision (Pydantic)
        |
    business-rule validation
        |
    optimizer

A response that does not validate is a failure, not something to repair by
guessing. Retry with the validation error fed back, then fail loudly.
"""

from __future__ import annotations

from reefcommand.coordinator.schemas import CoordinatorDecision
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction

MAX_VALIDATION_RETRIES = 2


def decide(evidence: FusedEvidence, actions: list[EligibleAction]) -> CoordinatorDecision:
    """Run the Coordinator for one site and return a validated decision."""
    raise NotImplementedError
