"""Thermal-stress investigator. Deterministic.

Read NOAA DHW, HotSpot, and outlook data, apply the documented thresholds, and
compute structured evidence.

Do not use an LLM here.
Comparing numeric thresholds is not a task that needs one, and keeping this
module deterministic is what makes the NOAA IoU check in docs/evaluation.md a
meaningful pipeline-correctness test.

The module output evaluated against NOAA Bleaching Alert Area is this module's
output alone, before fusion.
"""

from __future__ import annotations

from reefcommand.domain.enums import AlertLevel, Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.site import ReefSite

cause: Cause = Cause.THERMAL

# NOAA Coral Reef Watch alert thresholds, in degree C-weeks.
# See coralreefwatch.noaa.gov/product/5km/.
DHW_ALERT_LEVEL_1 = 4.0
DHW_ALERT_LEVEL_2 = 8.0


def alert_level_from_dhw(dhw: float, hotspot_c: float) -> AlertLevel:
    """Map DHW and HotSpot to a NOAA alert level using the documented rules."""
    raise NotImplementedError


def assess(site: ReefSite, observations: list[StructuredObservation]) -> CauseEvidence:
    """Compute thermal support deterministically from cached CRW products."""
    raise NotImplementedError
