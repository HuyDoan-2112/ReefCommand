"""Reef site endpoints.

Site payloads carry ecological_value and strategic_value separately, plus the
prototype-assumption disclaimer on the weights.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
def list_sites() -> list[dict[str, object]]:
    """All sites in the study area with both value scores and current evidence."""
    raise NotImplementedError


@router.get("/{site_id}/evidence")
def site_evidence(site_id: str) -> dict[str, object]:
    """Fused evidence for one site, including per-cause support, confidence, and citations."""
    raise NotImplementedError
