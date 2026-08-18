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


def _ordered(evidence: list[CauseEvidence]) -> list[CauseEvidence]:
    cause_order = {cause: index for index, cause in enumerate(Cause)}
    return sorted(
        evidence,
        key=lambda item: (-item.support, cause_order[item.cause]),
    )


def fuse(site_id: str, evidence: list[CauseEvidence]) -> FusedEvidence:
    """Reconcile four independent assessments into one summary for a site."""
    by_cause: dict[Cause, CauseEvidence] = {}
    for item in evidence:
        if item.cause in by_cause:
            raise ValueError(f"duplicate evidence for cause {item.cause.value!r}")
        by_cause[item.cause] = item

    ordered = _ordered(evidence)
    dominant_causes = [
        item.cause for item in ordered if item.support >= DOMINANCE_THRESHOLD
    ]
    return FusedEvidence(
        site_id=site_id,
        by_cause=by_cause,
        dominant_causes=dominant_causes,
        ambiguity=ambiguity_score(evidence),
        lowest_confidence=min((item.confidence for item in evidence), default=0.0),
        fused_at=datetime.now(UTC),
    )


def ambiguity_score(evidence: list[CauseEvidence]) -> float:
    """How close the leading causes are, on 0 to 1.

    Two causes at 0.68 and 0.65 score high.
    One cause at 0.91 against 0.17 scores low.
    """
    ordered = _ordered(evidence)
    if len(ordered) < 2:
        return 0.0
    return 1.0 - abs(ordered[0].support - ordered[1].support)
