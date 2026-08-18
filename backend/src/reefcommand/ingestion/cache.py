"""Local snapshot cache for external data.

Live external APIs are a demo liability, not a feature.
Everything the demo needs is pre-fetched into this cache before the event.

Usage pattern for every adapter:

    value, provenance = fetch_with_fallback(
        key="noaa_dhw:sombrero:2026-08-17",
        live=lambda: _call_noaa(...),
        to_payload=lambda obs: obs.model_dump(mode="json"),
        from_payload=lambda raw: CrwObservation.model_validate(raw),
        timeout_seconds=settings.external_timeout_seconds,
        source_url="https://coralreefwatch.noaa.gov/product/5km/",
    )

The audience should never see a spinner or an error, so a slow or failing live
call falls back to the cached snapshot instead of surfacing the failure.

Provenance is returned alongside the value and must be carried through to the
dashboard rather than dropped. A value served from disk is `cache`, never
`live`, so the demo can honestly answer "is this live right now".
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import UTC, datetime
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from reefcommand.config import CACHE_DIR, Settings, get_settings
from reefcommand.domain.enums import Provenance
from reefcommand.logging import get_logger

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_logger = get_logger(__name__)


class CacheError(Exception):
    """A stored snapshot exists but could not be read as a valid cache entry."""


class CacheMissError(CacheError):
    """No usable snapshot was available when one was required.

    Raised when forced-cache mode finds nothing on disk, or when a live call
    fails and there is no cached snapshot to fall back to.
    """


class CacheEntry(BaseModel):
    """A stored snapshot plus the metadata needed to report its age honestly.

    `fetched_at` is timezone-aware on purpose. A snapshot whose retrieval time
    cannot be stated in an unambiguous instant cannot be reported honestly, so a
    naive datetime is rejected at the boundary rather than stored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    fetched_at: AwareDatetime
    source_url: str | None = Field(default=None, min_length=1)
    payload: dict[str, object]


def _path_for(key: str, directory: Path) -> Path:
    """Map a cache key to a stable, collision-resistant file path.

    The readable prefix keeps the cache directory browsable by a human during
    demo prep. The hash suffix keeps two distinct keys that sanitize to the same
    prefix in separate files, so one never silently overwrites the other.
    """
    slug = _UNSAFE_FILENAME_CHARS.sub("_", key).strip("_")[:60]
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    prefix = f"{slug}-" if slug else ""
    return directory / f"{prefix}{digest}.json"


def read(key: str, directory: Path = CACHE_DIR) -> CacheEntry | None:
    """Return the cached entry for a key, or None when absent.

    A missing snapshot is a normal miss and returns None. A snapshot that exists
    but does not parse as a valid `CacheEntry` is a real defect and raises
    `CacheError` rather than being silently treated as absent.
    """
    path = _path_for(key, directory)
    if not path.exists():
        return None

    try:
        entry = CacheEntry.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise CacheError(f"corrupt cache entry at {path}") from exc
    except json.JSONDecodeError as exc:
        raise CacheError(f"unreadable cache entry at {path}") from exc

    if entry.key != key:
        # A hash collision on the filename would be astronomically unlikely, but
        # if one ever happened, serving the wrong key's data would be worse than
        # a miss. Treat it as absent so the caller re-fetches rather than lying.
        return None
    return entry


def write(entry: CacheEntry, directory: Path = CACHE_DIR) -> None:
    """Persist a snapshot to the cache directory.

    The write is atomic: the entry is written to a temporary file in the same
    directory and then renamed into place, so a crash mid-write never leaves a
    half-written snapshot that would later fail to parse.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = _path_for(entry.key, directory)
    payload = entry.model_dump_json(indent=2) + "\n"

    fd, tmp_name = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".json")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _call_with_timeout[T](live: Callable[[], T], timeout_seconds: float) -> T:
    """Run a synchronous live call under a wall-clock timeout.

    The call runs in a worker thread so a slow external service cannot hang the
    demo. On timeout the executor is torn down without waiting, so control
    returns promptly and the orphaned call finishes in the background.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(live)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        raise TimeoutError(f"live call exceeded {timeout_seconds}s") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def fetch_with_fallback[T](
    key: str,
    live: Callable[[], T],
    *,
    to_payload: Callable[[T], dict[str, object]],
    from_payload: Callable[[dict[str, object]], T],
    timeout_seconds: float,
    source_url: str | None = None,
    directory: Path = CACHE_DIR,
    settings: Settings | None = None,
) -> tuple[T, Provenance]:
    """Try the live call under a short timeout, fall back to cache.

    Returns the value and where it came from. Callers must carry the provenance
    through to the dashboard rather than dropping it.

    `to_payload` serializes a live value into the JSON-safe dict that is stored.
    `from_payload` rebuilds the value from that dict on a cache hit, so the same
    type is returned whether the value came from the network or from disk.

    With `force_cache` set, no live call is attempted at all: the snapshot is
    read from disk or a `CacheMissError` is raised. Otherwise a live success is
    written back to the cache and returned as `live`, and any timeout or error
    falls back to the cached snapshot when one exists.
    """
    settings = settings or get_settings()

    if settings.force_cache:
        entry = read(key, directory)
        if entry is not None:
            _logger.info(
                "external_data_served",
                key=key,
                provenance=Provenance.CACHE.value,
                source_url=entry.source_url,
                reason="force_cache",
            )
            return from_payload(entry.payload), Provenance.CACHE
        raise CacheMissError(f"force_cache is set but no snapshot exists for {key!r}")

    try:
        value = _call_with_timeout(live, timeout_seconds)
    except Exception as exc:
        entry = read(key, directory)
        if entry is not None:
            _logger.warning(
                "external_data_served",
                key=key,
                provenance=Provenance.CACHE.value,
                source_url=entry.source_url,
                reason="live_fetch_failed",
                error_type=type(exc).__name__,
            )
            return from_payload(entry.payload), Provenance.CACHE
        raise CacheMissError(f"live call for {key!r} failed and no cached snapshot exists") from exc

    write(
        CacheEntry(
            key=key,
            fetched_at=datetime.now(UTC),
            source_url=source_url,
            payload=to_payload(value),
        ),
        directory,
    )
    _logger.info(
        "external_data_served",
        key=key,
        provenance=Provenance.LIVE.value,
        source_url=source_url,
        reason="live_fetch_succeeded",
    )
    return value, Provenance.LIVE
