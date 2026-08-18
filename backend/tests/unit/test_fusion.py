"""Deterministic evidence-fusion tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.evidence.fusion import ambiguity_score, fuse

COMPUTED_AT = datetime(2026, 8, 18, tzinfo=UTC)


def _evidence(cause: Cause, support: float, confidence: float = 0.8) -> CauseEvidence:
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=confidence,
        rationale=f"Fixture rationale for {cause.value}.",
        computed_at=COMPUTED_AT,
    )


def test_fuse_preserves_supports_and_orders_dominant_causes() -> None:
    result = fuse(
        "cheeca_rocks",
        [
            _evidence(Cause.DISEASE, 0.7, confidence=0.6),
            _evidence(Cause.THERMAL, 0.8, confidence=0.9),
            _evidence(Cause.PHYSICAL, 0.2, confidence=0.7),
            _evidence(Cause.RUNOFF, 0.5, confidence=0.8),
        ],
    )

    assert result.site_id == "cheeca_rocks"
    assert result.dominant_causes == [Cause.THERMAL, Cause.DISEASE, Cause.RUNOFF]
    assert result.support(Cause.THERMAL) == pytest.approx(0.8)
    assert result.support(Cause.DISEASE) == pytest.approx(0.7)
    assert result.lowest_confidence == pytest.approx(0.6)
    assert result.ambiguity == pytest.approx(0.9)


def test_ambiguity_is_high_for_close_leaders_and_low_for_separated_leaders() -> None:
    close = [_evidence(Cause.THERMAL, 0.68), _evidence(Cause.DISEASE, 0.65)]
    separated = [_evidence(Cause.THERMAL, 0.91), _evidence(Cause.DISEASE, 0.17)]

    assert ambiguity_score(close) == pytest.approx(0.97)
    assert ambiguity_score(separated) == pytest.approx(0.26)


def test_missing_causes_have_zero_support_and_empty_fusion_is_valid() -> None:
    partial = fuse("sombrero", [_evidence(Cause.THERMAL, 0.4)])
    empty = fuse("sombrero", [])

    assert partial.support(Cause.DISEASE) == 0.0
    assert partial.dominant_causes == []
    assert partial.lowest_confidence == pytest.approx(0.8)
    assert empty.by_cause == {}
    assert empty.ambiguity == 0.0
    assert empty.lowest_confidence == 0.0


def test_duplicate_causes_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate evidence"):
        fuse(
            "looe_key",
            [_evidence(Cause.THERMAL, 0.4), _evidence(Cause.THERMAL, 0.8)],
        )
