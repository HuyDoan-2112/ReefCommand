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
from reefcommand.coordinator.schemas import CoordinatorDecision, CoordinatorOutput, SupportScore
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction
from reefcommand.llm.client import complete_structured

SCHEMA_VALIDATION_RETRIES = 2
BUSINESS_RULE_RETRIES = 2


class CoordinatorCompleter(Protocol):
    def __call__(
        self,
        system: str,
        user: str,
        schema: type[CoordinatorOutput],
    ) -> CoordinatorOutput:
        """Return one schema-validated Coordinator decision."""
        ...


def _default_complete(
    system: str,
    user: str,
    schema: type[CoordinatorOutput],
) -> CoordinatorOutput:
    return complete_structured(
        system,
        user,
        schema,
        max_retries=SCHEMA_VALIDATION_RETRIES,
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
    from reefcommand.coordinator.validation import BusinessRuleError, validate

    prompt = build_user_prompt(evidence, actions)
    for attempt in range(BUSINESS_RULE_RETRIES + 1):
        output = complete(SYSTEM_PROMPT, prompt, CoordinatorOutput)
        decision = CoordinatorDecision(
            **output.model_dump(),
            evidence_support_scores={
                cause: SupportScore(support=item.support, confidence=item.confidence)
                for cause, item in evidence.by_cause.items()
            },
        )
        try:
            return validate(decision, evidence, actions)
        except BusinessRuleError as exc:
            if attempt == BUSINESS_RULE_RETRIES:
                raise
            prompt = (
                f"{build_user_prompt(evidence, actions)}\n\n"
                f"The previous decision violated a business rule: {exc}. "
                "Return a corrected decision using only eligible actions."
            )
    raise AssertionError("Coordinator validation loop exited unexpectedly")
