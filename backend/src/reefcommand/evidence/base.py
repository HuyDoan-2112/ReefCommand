"""Shared investigator interface.

Every investigator takes the current site state and returns exactly one
CauseEvidence. Investigators do not see each other's output, which is what makes
the four signals independent.
"""

from __future__ import annotations

from typing import Protocol

from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite


class Investigator(Protocol):
    """One cause, one score."""

    cause: Cause

    def assess(
        self,
        site: ReefSite,
        observations: list[StructuredObservation],
    ) -> CauseEvidence:
        """Return this investigator's independent support score for its cause."""
        ...
