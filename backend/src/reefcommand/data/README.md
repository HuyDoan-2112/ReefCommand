# Data fixture contract

Persisted demo inputs use the versioned models in `reefcommand.domain.provenance`.
Every coherent record carries its own provenance metadata, so its origin cannot be inferred from a filename or folder.

## Version 1 shape

```yaml
metadata:
  schema_version: 1
  fixture_id: noaa_demo_window
  description: Cached NOAA observations for the demo replay window.
  created_at: 2026-08-17T12:00:00Z
records:
  - record_id: sombrero_2026-08-16
    data:
      site_id: sombrero
      observed_on: 2026-08-16
      degree_heating_weeks: 8.4
    provenance:
      kind: cache
      source: NOAA Coral Reef Watch 5km
      source_url: https://coralreefwatch.noaa.gov/product/5km/
      observed_at: 2026-08-16
      fetched_at: 2026-08-17T12:00:00Z
      note: Prefetched for the demo replay window.
```

## Provenance classes

| Kind | Meaning | Required metadata |
| --- | --- | --- |
| `live` | Retrieved from a real external source during the current operation. | `source`, timezone-aware `fetched_at` |
| `cache` | Persisted snapshot originally retrieved from a real external source. | `source`, timezone-aware `fetched_at` |
| `simulated` | Invented operational capacity or management scenario. | `source`, explanatory `note` |
| `synthetic` | Invented environmental signal or field observation. | `source`, explanatory `note` |

A persisted fixture record cannot be `live`.
Once a live response is written to disk, its fixture provenance is `cache` and retains the original fetch timestamp.

`observed_at` describes when the source says the condition occurred.
`fetched_at` describes when ReefCommand retrieved the external value.
Do not substitute one for the other.

The API may flatten `provenance.kind` to its public `provenance` field, but it must preserve source metadata and timestamps alongside the value.

## Record boundaries

One provenance object may cover a coherent record when every value in that record came from the same source and retrieval.
Split a record or add separately provenance-carrying records when values have different origins.
Never use document-level provenance to hide mixed real, cached, simulated, or synthetic values.

## Local snapshot cache

External snapshots are stored on disk by `reefcommand.ingestion.cache` so the demo never depends on a live call.
Each `CacheEntry` round-trips its cache key, a timezone-aware `fetched_at`, an optional `source_url`, and the JSON payload.
A naive `fetched_at` is rejected on write, because a snapshot whose retrieval instant is ambiguous cannot be reported honestly.

Adapters read and write through `fetch_with_fallback`, which returns the value together with its `Provenance`.
A live success is written back to the cache and returned as `live`; a value served from disk is returned as `cache`, never `live`.
With `force_cache` set, no live call is attempted at all: the snapshot is read from disk, or a `CacheMiss` is raised when none exists.
A slow or failing live call falls back to the cached snapshot under a short timeout, so a value is `cache` whenever the network did not actually answer.
