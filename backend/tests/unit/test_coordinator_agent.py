"""Tests for the Coordinator prompt and business-rule boundary."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reefcommand.coordinator.agent import decide
from reefcommand.coordinator.prompts import build_user_prompt
from reefcommand.coordinator.schemas import (
    ApprovedAction,
    CoordinatorDecision,
    EvidenceRequest,
    SupportScore,
)
from reefcommand.coordinator.validation import BusinessRuleError, validate
from reefcommand.domain.enums import ActionClass, Cause, EvidenceRequestType, Priority
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.intervention import EligibleAction, ResourceRequirement
from reefcommand.evidence.fusion import fuse


def _evidence() -> object:
    return fuse(
        "cheeca_rocks",
        [
            CauseEvidence(
                cause=Cause.THERMAL,
                support=0.82,
                confidence=0.91,
                rationale="High DHW.",
                computed_at=datetime(2023, 9, 15, tzinfo=UTC),
            ),
            CauseEvidence(
                cause=Cause.DISEASE,
                support=0.61,
                confidence=0.73,
                rationale="Lesion pattern.",
                computed_at=datetime(2023, 9, 15, tzinfo=UTC),
            ),
            CauseEvidence(
                cause=Cause.RUNOFF,
                support=0.13,
                confidence=0.64,
                rationale="Low rainfall support.",
                computed_at=datetime(2023, 9, 15, tzinfo=UTC),
            ),
            CauseEvidence(
                cause=Cause.PHYSICAL,
                support=0.05,
                confidence=0.78,
                rationale="No breakage.",
                computed_at=datetime(2023, 9, 15, tzinfo=UTC),
            ),
        ],
    )


def _action(*, unmet: list[str] | None = None, site_id: str = "cheeca_rocks") -> EligibleAction:
    return EligibleAction(
        site_id=site_id,
        action_id="intensive_monitoring",
        action_class=ActionClass.MONITORING,
        supporting_causes=[Cause.THERMAL, Cause.DISEASE],
        unmet_evidence_requirements=unmet or [],
        resources=ResourceRequirement(boats=1, dive_teams=1, dive_hours=3.0),
        expected_compatibility=0.7,
        provenance="NOAA protocol https://example.test/noaa-protocol",
    )


def _scores() -> dict[Cause, SupportScore]:
    return {
        Cause.THERMAL: SupportScore(support=0.82, confidence=0.91),
        Cause.DISEASE: SupportScore(support=0.61, confidence=0.73),
        Cause.RUNOFF: SupportScore(support=0.13, confidence=0.64),
        Cause.PHYSICAL: SupportScore(support=0.05, confidence=0.78),
    }


class FakeCompleter:
    def __init__(self, decision: CoordinatorDecision) -> None:
        self.decision = decision
        self.prompts: list[str] = []

    def __call__(
        self,
        system: str,
        user: str,
        schema: type[CoordinatorDecision],
    ) -> CoordinatorDecision:
        self.prompts.append(f"{system}\n{user}")
        return self.decision


def test_prompt_contains_fused_evidence_and_policy_candidates() -> None:
    prompt = build_user_prompt(_evidence(), [_action()])

    assert "Fused evidence" in prompt
    assert "intensive_monitoring" in prompt
    assert "support" in prompt
    assert "probability" not in prompt


def test_decide_returns_validated_approved_action() -> None:
    decision = CoordinatorDecision(
        site_id="cheeca_rocks",
        evidence_support_scores=_scores(),
        evidence_sufficient=True,
        additional_evidence_needed=False,
        approved_actions=[
            ApprovedAction(
                action_id="intensive_monitoring",
                priority=Priority.HIGH,
                rationale="Thermal and disease support exceed the monitoring bar.",
            )
        ],
        reasoning_summary="Act on the eligible monitoring action.",
    )
    completer = FakeCompleter(decision)

    result = decide(_evidence(), [_action()], completer=completer)

    assert result == decision
    assert "Policy-eligible candidate actions" in completer.prompts[0]


def test_decide_can_request_more_evidence() -> None:
    decision = CoordinatorDecision(
        site_id="cheeca_rocks",
        evidence_support_scores=_scores(),
        evidence_sufficient=False,
        additional_evidence_needed=True,
        next_evidence=[
            EvidenceRequest(
                type=EvidenceRequestType.CLOSE_RANGE_LESION_IMAGE,
                priority=1,
                rationale="Thermal and disease support imply different actions.",
            )
        ],
        reasoning_summary="Request lesion imagery before acting.",
    )

    assert decide(_evidence(), [_action()], completer=FakeCompleter(decision)) == decision


def test_validation_rejects_unknown_action() -> None:
    decision = CoordinatorDecision(
        site_id="cheeca_rocks",
        evidence_support_scores=_scores(),
        evidence_sufficient=True,
        additional_evidence_needed=False,
        approved_actions=[
            ApprovedAction(
                action_id="invented_action",
                priority=Priority.HIGH,
                rationale="The model invented this.",
            )
        ],
        reasoning_summary="Invalid.",
    )

    with pytest.raises(BusinessRuleError, match="unknown or ineligible"):
        validate(decision, "cheeca_rocks", [_action()])


def test_validation_rejects_unmet_requirement_and_site_mismatch() -> None:
    unmet_decision = CoordinatorDecision(
        site_id="cheeca_rocks",
        evidence_support_scores=_scores(),
        evidence_sufficient=True,
        additional_evidence_needed=False,
        approved_actions=[
            ApprovedAction(
                action_id="intensive_monitoring",
                priority=Priority.HIGH,
                rationale="Invalid while evidence is missing.",
            )
        ],
        reasoning_summary="Invalid.",
    )
    with pytest.raises(BusinessRuleError, match="unmet evidence"):
        validate(unmet_decision, "cheeca_rocks", [_action(unmet=["Need a report"])])

    with pytest.raises(BusinessRuleError, match="does not match"):
        validate(
            unmet_decision.model_copy(update={"site_id": "sombrero"}),
            "cheeca_rocks",
            [_action()],
        )
