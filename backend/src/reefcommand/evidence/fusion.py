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

from reefcommand.domain.evidence import CauseEvidence, FusedEvidence

# Support at or above this level counts a cause as "in play" for the site.
DOMINANCE_THRESHOLD = 0.5

# When the top two in-play causes are within this margin, the case is ambiguous.
AMBIGUITY_MARGIN = 0.15


def fuse(site_id: str, evidence: list[CauseEvidence]) -> FusedEvidence:
    """Reconcile four independent assessments into one summary for a site."""
    raise NotImplementedError


def ambiguity_score(evidence: list[CauseEvidence]) -> float:
    """How close the leading causes are, on 0 to 1.

    Two causes at 0.68 and 0.65 score high.
    One cause at 0.91 against 0.17 scores low.
    """
    raise NotImplementedError
