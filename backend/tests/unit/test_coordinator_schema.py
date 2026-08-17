"""Schema invariants for the Coordinator's structured output.

These are the rules that stop malformed model output from reaching the optimizer.
They are worth testing directly, because the whole reliability argument rests on
them failing loudly.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from reefcommand.coordinator.schemas import (
    ApprovedAction,
    CoordinatorDecision,
    EvidenceRequest,
    SupportScore,
)
from reefcommand.domain.enums import Cause, EvidenceRequestType, Priority


def _scores() -> dict[Cause, SupportScore]:
    return {
        Cause.THERMAL: SupportScore(support=0.82, confidence=0.91),
        Cause.DISEASE: SupportScore(support=0.61, confidence=0.73),
        Cause.RUNOFF: SupportScore(support=0.13, confidence=0.64),
        Cause.PHYSICAL: SupportScore(support=0.05, confidence=0.78),
    }


def test_support_scores_need_not_sum_to_one() -> None:
    """Support scores are not probabilities and are not normalized."""
    scores = _scores()
    total = sum(entry.support for entry in scores.values())
    assert total > 1.0

    decision = CoordinatorDecision(
        site_id="sombrero",
        evidence_support_scores=scores,
        evidence_sufficient=False,
        additional_evidence_needed=True,
        next_evidence=[
            EvidenceRequest(
                type=EvidenceRequestType.CLOSE_RANGE_LESION_IMAGE,
                priority=1,
                rationale="Thermal and disease are both well supported.",
            )
        ],
        reasoning_summary="Ambiguous between thermal and disease.",
    )
    assert decision.additional_evidence_needed is True


def test_sufficient_and_needed_cannot_both_be_true() -> None:
    with pytest.raises(ValidationError):
        CoordinatorDecision(
            site_id="sombrero",
            evidence_support_scores=_scores(),
            evidence_sufficient=True,
            additional_evidence_needed=True,
            reasoning_summary="Contradictory.",
        )


def test_needing_evidence_requires_naming_it() -> None:
    with pytest.raises(ValidationError):
        CoordinatorDecision(
            site_id="sombrero",
            evidence_support_scores=_scores(),
            evidence_sufficient=False,
            additional_evidence_needed=True,
            next_evidence=[],
            reasoning_summary="Says it needs evidence but requests none.",
        )


def test_sufficient_evidence_requires_an_approved_action() -> None:
    with pytest.raises(ValidationError):
        CoordinatorDecision(
            site_id="sombrero",
            evidence_support_scores=_scores(),
            evidence_sufficient=True,
            additional_evidence_needed=False,
            approved_actions=[],
            reasoning_summary="Says act, but approves nothing.",
        )


def test_extra_fields_are_rejected() -> None:
    """The optimizer must never receive an unrecognized field it might act on."""
    with pytest.raises(ValidationError):
        CoordinatorDecision.model_validate(
            {
                "site_id": "sombrero",
                "evidence_support_scores": {"thermal": {"support": 0.9, "confidence": 0.9}},
                "evidence_sufficient": True,
                "additional_evidence_needed": False,
                "approved_actions": [
                    {
                        "action_id": "intensive_monitoring",
                        "priority": Priority.HIGH.value,
                        "rationale": "Clear thermal signal.",
                    }
                ],
                "reasoning_summary": "Proceed.",
                "assign_boat": "boat_a",
            }
        )


def test_approved_action_requires_a_rationale() -> None:
    with pytest.raises(ValidationError):
        ApprovedAction(action_id="intensive_monitoring", priority=Priority.HIGH, rationale="")
