"""Reef site endpoints.

Site payloads carry ecological_value and strategic_value separately, plus the
prototype-assumption disclaimer on the weights.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from reefcommand.api.schemas import SiteView
from reefcommand.api.state import peek_current_plan
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.orchestration.pipeline import load_sites, state_for_plan

router = APIRouter(prefix="/sites", tags=["sites"])

# The site's own latitude and longitude are computed from its location block, so
# they cannot be passed back into the model when composing the response view.
_COMPUTED_SITE_FIELDS = {"latitude", "longitude"}


@router.get("", response_model=list[SiteView])
def list_sites() -> list[SiteView]:
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
        SiteView(
            **site.model_dump(exclude=_COMPUTED_SITE_FIELDS),
            scores=state.problem.scores[site.site_id],
            dominant_causes=state.evidence_by_site[site.site_id].dominant_causes,
            current_assignment=assignments_by_site.get(site.site_id),
            deferred=deferred_by_site.get(site.site_id),
        )
        for site in sites
    ]


@router.get("/{site_id}/evidence", response_model=FusedEvidence)
def site_evidence(site_id: str) -> FusedEvidence:
    """Fused evidence for one site, including per-cause support, confidence, and citations."""
    plan = peek_current_plan()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}")
    state = state_for_plan(plan.plan_id)
    if state is None or site_id not in state.evidence_by_site:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}")
    return state.evidence_by_site[site_id]
