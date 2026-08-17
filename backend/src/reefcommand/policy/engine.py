"""Intervention policy engine. Deterministic.

Runs before the Coordinator ever sees a case.
It answers: given this fused evidence and this site, which catalog actions are
policy-eligible and source-backed, and what evidence does each still lack.

This is what makes the Coordinator's question concrete.
The Coordinator is never asked "is the evidence sufficient" in the abstract.
It is asked against a pre-computed list of eligible actions and their evidence
requirements.

Eligibility is not a promise of effectiveness.
Shading is the standing example: a peer-reviewed field study found no measurable
benefit at two coral nursery sites, which is why requirements, contraindications,
and provenance are checked per site rather than assumed.
"""

from __future__ import annotations

from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.site import ReefSite


def eligible_actions(site: ReefSite, evidence: FusedEvidence) -> list[EligibleAction]:
    """Return the catalog actions that are policy-eligible for this site right now.

    An action with a non-empty `unmet_evidence_requirements` is still returned.
    It is eligible in principle but not yet actionable, and the Coordinator needs
    to see it in order to know what observation would unlock it.
    """
    raise NotImplementedError


def check_contraindications(site: ReefSite, action_id: str) -> list[str]:
    """Return the contraindications that currently apply. Empty means none."""
    raise NotImplementedError
