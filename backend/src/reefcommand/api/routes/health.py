"""Health and data-provenance endpoints.

`/health/data-sources` reports, per source, whether the last value came from a
live call or from cache and how old the snapshot is.
The demo team needs to be able to answer "is this live right now" honestly and
without guessing.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@router.get("/data-sources")
def data_sources() -> dict[str, object]:
    """Per-source live-versus-cache status and snapshot age."""
    raise NotImplementedError
