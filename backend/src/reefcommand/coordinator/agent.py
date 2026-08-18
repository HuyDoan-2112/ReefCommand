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

from typing import Protocol

from reefcommand.coordinator.prompts import SYSTEM_PROMPT, build_user_prompt
from reefcommand.coordinator.schemas import CoordinatorDecision
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction
from reefcommand.llm.client import complete_structured

MAX_VALIDATION_RETRIES = 2


class CoordinatorCompleter(Protocol):
    def __call__(
        self,
        system: str,
        user: str,
        schema: type[CoordinatorDecision],
    ) -> CoordinatorDecision:
        """Return one schema-validated Coordinator decision."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[CoordinatorDecision],
) -> CoordinatorDecision:
    return complete_structured(
        system,
        user,
        schema,
        max_retries=MAX_VALIDATION_RETRIES,
    )


def decide(
    evidence: FusedEvidence,
    actions: list[EligibleAction],
    *,
    completer: CoordinatorCompleter | None = None,
) -> CoordinatorDecision:
    """Run the Coordinator for one site and return a validated decision."""
    if any(action.site_id != evidence.site_id for action in actions):
        raise ValueError("all Coordinator actions must use the fused evidence site_id")
    complete = completer or _default_complete
    decision = complete(SYSTEM_PROMPT, build_user_prompt(evidence, actions), CoordinatorDecision)
    from reefcommand.coordinator.validation import validate

    return validate(decision, evidence.site_id, actions)
