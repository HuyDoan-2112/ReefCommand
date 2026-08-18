"""The Coordinator cannot approve an action the policy engine did not offer.

This is the load-bearing rule of the architecture: the LLM does not invent
interventions.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reefcommand.coordinator.schemas import ApprovedAction, CoordinatorDecision, SupportScore
from reefcommand.coordinator.validation import BusinessRuleError, validate
from reefcommand.domain.enums import Cause, Priority
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.intervention import EligibleAction, ResourceRequirement
from reefcommand.evidence.fusion import fuse


def _evidence() -> object:
    return fuse(
        "cheeca_rocks",
        [
            CauseEvidence(
                cause=Cause.THERMAL,
                support=0.8,
                confidence=0.8,
                rationale="heat",
                computed_at=datetime.now(UTC),
            ),
            CauseEvidence(
                cause=Cause.DISEASE,
                support=0.7,
                confidence=0.8,
                rationale="lesion",
                computed_at=datetime.now(UTC),
            ),
            CauseEvidence(
                cause=Cause.RUNOFF,
                support=0.1,
                confidence=0.8,
                rationale="rain",
                computed_at=datetime.now(UTC),
            ),
            CauseEvidence(
                cause=Cause.PHYSICAL,
                support=0.1,
                confidence=0.8,
                rationale="no damage",
                computed_at=datetime.now(UTC),
            ),
        ],
    )


def _action(
    *, action_id: str = "intensive_monitoring", unmet: list[str] | None = None
) -> EligibleAction:
    return EligibleAction(
        site_id="cheeca_rocks",
        action_id=action_id,
        action_class="monitoring",
        supporting_causes=[Cause.THERMAL],
        unmet_evidence_requirements=unmet or [],
        resources=ResourceRequirement(boats=1, dive_teams=1, dive_hours=3.0),
        expected_compatibility=0.7,
        provenance="NOAA protocol https://example.test/protocol",
    )


def _decision(action_id: str) -> CoordinatorDecision:
    evidence = _evidence()
    return CoordinatorDecision(
        site_id="cheeca_rocks",
        evidence_support_scores={
            cause: SupportScore(support=item.support, confidence=item.confidence)
            for cause, item in evidence.by_cause.items()
        },
        evidence_sufficient=True,
        additional_evidence_needed=False,
        approved_actions=[
            ApprovedAction(action_id=action_id, priority=Priority.HIGH, rationale="test")
        ],
        reasoning_summary="test",
    )


def test_unknown_action_id_is_rejected() -> None:
    with pytest.raises(BusinessRuleError, match="unknown or ineligible"):
        validate(_decision("invented"), _evidence(), [_action()])


def test_action_with_unmet_evidence_requirements_is_rejected() -> None:
    with pytest.raises(BusinessRuleError, match="unmet evidence"):
        validate(
            _decision("intensive_monitoring"),
            _evidence(),
            [_action(unmet=["Need a field report"])],
        )


def test_contraindicated_action_is_rejected() -> None:
    with pytest.raises(BusinessRuleError, match="unknown or ineligible"):
        validate(_decision("temporary_shading"), _evidence(), [_action()])
