"""Deterministic fusion tests for the four independent cause assessments."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.evidence.fusion import ambiguity_score, fuse


def _evidence(cause: Cause, support: float, confidence: float = 0.8) -> CauseEvidence:
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=confidence,
        display_summary=f"Fixture summary for {cause.value}.",
        key_findings=[f"Fixture finding for {cause.value}."],
        rationale=f"fixture {cause.value}",
        computed_at=datetime(2023, 9, 15, tzinfo=UTC),
    )


def _all() -> list[CauseEvidence]:
    return [
        _evidence(Cause.THERMAL, 0.82, 0.91),
        _evidence(Cause.DISEASE, 0.61, 0.73),
        _evidence(Cause.RUNOFF, 0.13, 0.64),
        _evidence(Cause.PHYSICAL, 0.05, 0.78),
    ]


def test_fusion_preserves_all_support_scores_without_normalizing() -> None:
    fused = fuse("sombrero", _all())

    assert fused.site_id == "sombrero"
    assert fused.support(Cause.THERMAL) == 0.82
    assert fused.support(Cause.DISEASE) == 0.61
    assert fused.dominant_causes == [Cause.THERMAL, Cause.DISEASE]
    assert fused.lowest_confidence == pytest.approx(0.64)
    assert fused.ambiguity == 0.0


def test_close_top_scores_are_ambiguous() -> None:
    scores = [_evidence(Cause.THERMAL, 0.68), _evidence(Cause.DISEASE, 0.65)]

    assert ambiguity_score(scores) == pytest.approx(0.8)


def test_quiet_site_is_not_ambiguous() -> None:
    scores = [
        _evidence(Cause.THERMAL, 0.10),
        _evidence(Cause.DISEASE, 0.08),
        _evidence(Cause.RUNOFF, 0.05),
        _evidence(Cause.PHYSICAL, 0.02),
    ]

    assert ambiguity_score(scores) == 0.0


def test_fusion_requires_exactly_one_assessment_per_cause() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        fuse("sombrero", _all()[:-1])

    with pytest.raises(ValueError, match="one assessment"):
        fuse(
            "sombrero",
            [
                *_all()[:2],
                _evidence(Cause.THERMAL, 0.2),
                _evidence(Cause.PHYSICAL, 0.1),
            ],
        )


def test_card_copy_rejects_oversized_agent_output() -> None:
    with pytest.raises(ValidationError, match="display_summary"):
        CauseEvidence(
            cause=Cause.THERMAL,
            support=0.5,
            confidence=0.5,
            display_summary="x" * 181,
            key_findings=["Short finding."],
            rationale="Full audit rationale.",
            computed_at=datetime(2023, 9, 15, tzinfo=UTC),
        )

    with pytest.raises(ValidationError, match="key_findings"):
        CauseEvidence(
            cause=Cause.THERMAL,
            support=0.5,
            confidence=0.5,
            display_summary="Short summary.",
            key_findings=["x" * 111],
            rationale="Full audit rationale.",
            computed_at=datetime(2023, 9, 15, tzinfo=UTC),
        )
