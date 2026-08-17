"""Physical-damage investigator. LLM plus tools.

Combines reports of broken coral, storm history, wave and storm information,
vessel activity, and anchor or grounding observations.

Same synthetic-labeling rule as runoff.
"""

from __future__ import annotations

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite

cause: Cause = Cause.PHYSICAL


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Combine breakage reports with storm and vessel history."""
    raise NotImplementedError
