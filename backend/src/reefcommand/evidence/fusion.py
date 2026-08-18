"""Deterministic evidence fusion.

Combines the four separately generated, non-mutually-exclusive support scores
into one reconciled evidence summary per site.

No LLM call happens here.
This is aggregation of the summary only.
The underlying per-cause scores are not normalized against each other, because
they are not competing shares of a single probability mass.

What fusion does compute is `ambiguity`: how close the leading causes are.
High ambiguity is precisely the situation the Coordinator resolves by requesting
another observation rather than committing to an intervention.
"""

from __future__ import annotations

from datetime import UTC, datetime

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence, FusedEvidence

# Support at or above this level counts a cause as "in play" for the site.
DOMINANCE_THRESHOLD = 0.5

# When the top two in-play causes are within this margin, the case is ambiguous.
AMBIGUITY_MARGIN = 0.15


def fuse(site_id: str, evidence: list[CauseEvidence]) -> FusedEvidence:
    """Reconcile four independent assessments into one summary for a site."""
    expected = set(Cause)
    if len(evidence) != len(expected):
        raise ValueError(
            "fusion requires exactly one assessment for each cause: "
            f"{sorted(expected, key=lambda item: item.value)}"
        )
    if any(item.cause not in expected for item in evidence):
        raise ValueError("fusion received an unknown cause")
    if len({item.cause for item in evidence}) != len(expected):
        raise ValueError("fusion requires one assessment per cause")
    by_cause = {item.cause: item for item in evidence}
    ordered = sorted(evidence, key=lambda item: item.support, reverse=True)
    dominant = [item.cause for item in ordered if item.support >= DOMINANCE_THRESHOLD]
    return FusedEvidence(
        site_id=site_id,
        by_cause=by_cause,
        dominant_causes=dominant,
        ambiguity=ambiguity_score(evidence),
        lowest_confidence=min(item.confidence for item in evidence),
        fused_at=datetime.now(UTC),
    )


def ambiguity_score(evidence: list[CauseEvidence]) -> float:
    """How close the leading causes are, on 0 to 1.

    Two causes at 0.68 and 0.65 score high.
    One cause at 0.91 against 0.17 scores low.
    """
    if len(evidence) < 2:
        return 0.0
    ordered = sorted((item.support for item in evidence), reverse=True)
    gap = ordered[0] - ordered[1]
    return max(0.0, min(1.0, 1.0 - gap / AMBIGUITY_MARGIN))
