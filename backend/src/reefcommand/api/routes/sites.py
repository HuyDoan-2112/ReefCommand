"""Reef site endpoints.

Site payloads carry ecological_value and strategic_value separately, plus the
prototype-assumption disclaimer on the weights.
"""

from __future__ import annotations

from fastapi import APIRouter

from reefcommand.api.state import peek_current_plan
from reefcommand.orchestration.pipeline import load_sites, state_for_plan

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
def list_sites() -> list[dict[str, object]]:
    """All sites in the study area with both value scores and current evidence."""
    plan = peek_current_plan()
    if plan is None:
        return []
    state = state_for_plan(plan.plan_id)
    if state is None:
        return []
    assignments_by_site = {assignment.site_id: assignment for assignment in plan.assignments}
    deferred_by_site = {site.site_id: site for site in plan.deferred}
    sites = load_sites(state.site_ids)
    return [
        {
            **site.model_dump(mode="json"),
            "scores": state.problem.scores[site.site_id].model_dump(mode="json"),
            "dominant_causes": [
                cause.value for cause in state.evidence_by_site[site.site_id].dominant_causes
            ],
            "current_assignment": (
                assignments_by_site[site.site_id].model_dump(mode="json")
                if site.site_id in assignments_by_site
                else None
            ),
            "deferred": (
                deferred_by_site[site.site_id].model_dump(mode="json")
                if site.site_id in deferred_by_site
                else None
            ),
        }
        for site in sites
    ]


@router.get("/{site_id}/evidence")
def site_evidence(site_id: str) -> dict[str, object]:
    """Fused evidence for one site, including per-cause support, confidence, and citations."""
    from fastapi import HTTPException

    plan = peek_current_plan()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}")
    state = state_for_plan(plan.plan_id)
    if state is None or site_id not in state.evidence_by_site:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}")
    return state.evidence_by_site[site_id].model_dump(mode="json")
