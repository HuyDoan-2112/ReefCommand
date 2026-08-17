"""Response plan endpoints.

The plan payload includes what evidence supported each decision, what uncertainty
remains, which constraints were binding, and why each action was considered
compatible. Those are part of the contract, not optional extras.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/current")
def current_plan() -> dict[str, object]:
    """The current response plan."""
    raise NotImplementedError


@router.post("/recompute")
def recompute() -> dict[str, object]:
    """Force a recompute. Returns the new plan and its latency."""
    raise NotImplementedError
