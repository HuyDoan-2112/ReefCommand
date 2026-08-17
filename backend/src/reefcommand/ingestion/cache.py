"""Local snapshot cache for external data.

Live external APIs are a demo liability, not a feature.
Everything the demo needs is pre-fetched into this cache before the event.

Usage pattern for every adapter:

    value = fetch_with_fallback(
        key="noaa_dhw:2026-08-17",
        live=lambda: _call_noaa(...),
        timeout_seconds=settings.external_timeout_seconds,
    )

The audience should never see a spinner or an error.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel

from reefcommand.domain.enums import Provenance


class CacheEntry(BaseModel):
    """A stored snapshot plus the metadata needed to report its age honestly."""

    key: str
    fetched_at: datetime
    source_url: str | None = None
    payload: dict


def read(key: str) -> CacheEntry | None:
    """Return the cached entry for a key, or None when absent."""
    raise NotImplementedError


def write(entry: CacheEntry) -> None:
    """Persist a snapshot to the cache directory."""
    raise NotImplementedError


def fetch_with_fallback[T](
    key: str,
    live: Callable[[], T],
    timeout_seconds: float,
) -> tuple[T, Provenance]:
    """Try the live call under a short timeout, fall back to cache.

    Returns the value and where it came from.
    Callers must carry the provenance through to the dashboard rather than
    dropping it.
    """
    raise NotImplementedError
