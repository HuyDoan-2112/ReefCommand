"""Health and data-provenance endpoints.

`/health/data-sources` reports, per source, whether the last value came from a
live call or from cache and how old the snapshot is.
The demo team needs to be able to answer "is this live right now" honestly and
without guessing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from reefcommand.api.state import current_plan
from reefcommand.domain.enums import Provenance
from reefcommand.orchestration.pipeline import state_for_plan

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@router.get("/data-sources")
def data_sources() -> dict[str, object]:
    """Per-source live-versus-cache status and snapshot age."""
    plan = current_plan()
    state = state_for_plan(plan.plan_id)
    sources: dict[str, set[Provenance]] = {}
    if state:
        for evidence in state.evidence_by_site.values():
            for entry in evidence.by_cause.values():
                for citation in entry.citations:
                    sources.setdefault(citation.source, set()).add(citation.provenance)

    payload = []
    for source, provenances in sorted(sources.items()):
        if provenances <= {Provenance.SYNTHETIC, Provenance.SIMULATED}:
            status = "synthetic_fixture"
        elif Provenance.LIVE in provenances:
            status = "live"
        else:
            status = "cache"
        payload.append(
            {
                "source": source,
                "provenance": sorted(provenance.value for provenance in provenances),
                "status": status,
                "note": (
                    "Offline demo input. Synthetic or simulated values are not live measurements."
                    if status == "synthetic_fixture"
                    else "Status reflects the provenance carried by the current evidence snapshot."
                ),
            }
        )
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "sources": payload,
    }
