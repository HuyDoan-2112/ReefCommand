"""Health and data-provenance endpoints.

`/health/data-sources` reports, per source, whether the last value came from a
live call or from cache and how old the snapshot is.
The demo team needs to be able to answer "is this live right now" honestly and
without guessing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from reefcommand.api.schemas import (
    DataSourcesHealth,
    DataSourceStatus,
    DataSourceStatusValue,
    HealthStatus,
)
from reefcommand.api.state import peek_current_plan
from reefcommand.domain.enums import Provenance
from reefcommand.orchestration.pipeline import state_for_plan

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthStatus)
def health() -> HealthStatus:
    """Liveness check."""
    return HealthStatus(status="ok")


@router.get("/data-sources", response_model=DataSourcesHealth)
def data_sources() -> DataSourcesHealth:
    """Per-source live-versus-cache status and snapshot age."""
    plan = peek_current_plan()
    if plan is None:
        return DataSourcesHealth(
            checked_at=datetime.now(UTC),
            sources=[],
            status="no_plan",
        )
    state = state_for_plan(plan.plan_id)
    sources: dict[str, set[Provenance]] = {}
    if state:
        for evidence in state.evidence_by_site.values():
            for entry in evidence.by_cause.values():
                for citation in entry.citations:
                    sources.setdefault(citation.source, set()).add(citation.provenance)

    payload: list[DataSourceStatus] = []
    for source, provenances in sorted(sources.items()):
        status: DataSourceStatusValue
        if provenances <= {Provenance.SYNTHETIC, Provenance.SIMULATED}:
            status = "synthetic_fixture"
        elif Provenance.LIVE in provenances:
            status = "live"
        else:
            status = "cache"
        payload.append(
            DataSourceStatus(
                source=source,
                provenance=sorted(provenances, key=lambda item: item.value),
                status=status,
                note=(
                    "Offline demo input. Synthetic or simulated values are not live measurements."
                    if status == "synthetic_fixture"
                    else "Status reflects the provenance carried by the current evidence snapshot."
                ),
            )
        )
    return DataSourcesHealth(checked_at=datetime.now(UTC), sources=payload)
