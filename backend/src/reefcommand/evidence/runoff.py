"""Runoff and water-quality investigator. LLM plus tools.

Combines diver descriptions, recent rainfall, turbidity information, geographic
context, proximity to runoff sources, and water-quality evidence.

If a real rainfall API is not wired up, the rainfall input is a clearly labeled
synthetic signal and that label travels into the citations.
"""

from __future__ import annotations

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite

cause: Cause = Cause.RUNOFF


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine turbidity and sediment reports with the rainfall signal."""
    raise NotImplementedError
