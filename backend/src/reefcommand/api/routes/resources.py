"""Operational capacity endpoints.

Every response carries the simulated-data banner.
The dashboard renders it above any plan built from the scenario.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("/scenario")
def get_scenario() -> dict[str, object]:
    """The active simulated resource scenario."""
    raise NotImplementedError


@router.patch("/scenario")
def update_scenario() -> dict[str, object]:
    """Change capacity, for example marking a boat unavailable, and trigger re-planning."""
    raise NotImplementedError
