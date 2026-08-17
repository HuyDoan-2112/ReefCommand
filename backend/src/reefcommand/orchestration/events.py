"""Events that can invalidate the current plan.

Two kinds, and they invalidate different amounts of work.

NewEvidence changes what we believe about a site, so the pipeline re-runs from
the affected investigators forward.

ResourceChange does not change any evidence, so investigators, fusion, policy,
and the Coordinator can all be skipped. Only the optimizer re-runs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from reefcommand.domain.observation import FieldReport


class NewEvidence(BaseModel):
    """A field report arrived.

    For example: "Cheeca Rocks now shows localized tissue loss with visible lesions."
    """

    received_at: datetime
    report: FieldReport


class ResourceChange(BaseModel):
    """Capacity changed. For example, Boat B became unavailable.

    The existing plan may become infeasible, and the system detects that rather
    than waiting to be asked.
    """

    received_at: datetime
    scenario_id: str
    description: str


PlanEvent = NewEvidence | ResourceChange
