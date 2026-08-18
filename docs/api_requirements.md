# API requirements

The contract between the backend and the dashboard.

This document is the agreement.
The generated OpenAPI schema at `/docs` is the machine-readable version, and the frontend generates its types from it rather than hand-writing them.

Changing anything here is a shared-contract change: its own pull request, reviewed by both tracks.
See `.agents/rules/multi-agent-rules.md`.

## Principles

**Explanations are fields, not UI decoration.**
The dashboard must explain what evidence supported a decision, what uncertainty remains, what constraints caused the trade-offs, and why an action was considered compatible.
Those all arrive from the backend as data, so the frontend cannot accidentally omit one and the backend cannot quietly stop producing one.

**Provenance travels with every external value.**
`live`, `cache`, `simulated`, or `synthetic`.
Never optional, never strippable in a response model.

**Nothing overstates what it proves.**
Support scores are `support`, not `probability`.
Prototype weights carry their disclaimer in the payload.

**Fixtures come first.**
Every endpoint returns a valid hand-written fixture before the pipeline exists, so the frontend is never blocked.
The shapes below are the shapes on day one.

## Endpoints

### `GET /health`

Liveness. Returns `{"status": "ok"}`.

### `GET /health/data-sources`

Per external source: whether the last value came from a live call or cache, and the snapshot age.
This endpoint never starts a planning run.
Before the first plan is published it returns `status: "no_plan"` with an empty source list.

```json
{
  "sources": [
    {
      "name": "NOAA Coral Reef Watch",
      "provenance": "cache",
      "fetched_at": "2026-08-16T22:14:03Z",
      "age_seconds": 74521,
      "note": "Prefetched for the demo replay window"
    },
    {
      "name": "AGRRA SCTLD Tracking Map",
      "provenance": "cache",
      "fetched_at": "2026-08-16T22:15:11Z",
      "age_seconds": 74453,
      "note": "Curated snapshot"
    },
    {
      "name": "Rainfall",
      "provenance": "synthetic",
      "fetched_at": null,
      "age_seconds": null,
      "note": "Labeled synthetic signal, no live source wired up"
    }
  ],
  "force_cache": true
}
```

`force_cache` reflects `REEFCOMMAND_FORCE_CACHE`, so the demo team can confirm at a glance that no live call will be attempted.

### `GET /sites`

All sites in the study area with both value scores.

```json
{
  "sites": [
    {
      "site_id": "sombrero",
      "name": "Sombrero Reef",
      "latitude": 24.6265,
      "longitude": -81.1109,
      "location": {
        "latitude": 24.6265,
        "longitude": -81.1109,
        "location_basis": "site centroid from the NOAA Mission: Iconic Reefs zone boundary",
        "zone_name_in_source": "Sombrero Reef",
        "zone_span_km": null,
        "provenance": {
          "kind": "cache",
          "source": "NOAA Mission: Iconic Reefs",
          "source_url": "https://sanctuaries.noaa.gov/iconic-reefs/",
          "observed_at": null,
          "fetched_at": "2026-08-16T22:14:03Z",
          "note": "Curated snapshot"
        }
      },
      "measurements": {
        "coral_cover_pct": 6.4,
        "species_richness": 21,
        "sampling": {
          "program": "CREMP",
          "sampling_design": "fixed transects with photo point counts",
          "reference_years": [2024],
          "sample_n": 5,
          "sample_unit": "sample unit",
          "sample_sd_pct": 1.8,
          "matching_method": "named site in the monitoring programme",
          "matching_distance_km": 0.0,
          "habitat_types": ["offshore patch"],
          "richness_definition": "observed coral taxa in the cited sample",
          "includes_millepora": true,
          "station_ids": ["..."]
        },
        "provenance": {
          "kind": "cache",
          "source": "CREMP station ...",
          "source_url": "https://ocean.floridamarine.org/",
          "observed_at": null,
          "fetched_at": "2026-08-16T22:14:03Z",
          "note": "Curated snapshot"
        }
      },
      "scores": {
        "ecological_value": 0.71,
        "strategic_value": 0.68,
        "weights_are_prototype_assumptions": true
      },
      "has_active_restoration": true,
      "restoration_investment": {
        "value": 0.5,
        "provenance": {
          "kind": "simulated",
          "source": "ReefCommand prototype assumption",
          "source_url": null,
          "observed_at": null,
          "fetched_at": null,
          "note": "SIMULATED management commitment weight, not published expenditure."
        }
      }
    }
  ],
  "weights_disclaimer": "Scoring weights are prototype assumptions, not scientific claims."
}
```

Both scores are always returned.
The frontend shows `strategic_value` as what drives allocation and `ecological_value` as the investment-agnostic number.

The site model stores coordinates in the nested `location` block, while `latitude` and `longitude` are also serialized as computed convenience fields for the current flat API shape.

Measurement provenance is structured, and sampling metadata keeps the monitoring programme, sample size, matching method, and programme-specific caveats next to the measurements.

`restoration_investment` is an object because its normalized value is simulated and must travel with its provenance.

### `GET /sites/{site_id}/evidence`

Fused evidence for one site.

```json
{
  "site_id": "sombrero",
  "fused_at": "2026-08-17T14:02:11Z",
  "by_cause": {
    "thermal": {
      "support": 0.82,
      "confidence": 0.91,
      "rationale": "DHW 8.4 at alert level 2 for the past 6 days.",
      "citations": [
        {
          "source": "NOAA Coral Reef Watch 5km",
          "reference": "https://coralreefwatch.noaa.gov/product/5km/",
          "observed_at": "2026-08-16",
          "review_status": null,
          "reporting_organization": "NOAA",
          "provenance": "cache"
        }
      ]
    },
    "disease": { "support": 0.61, "confidence": 0.73, "rationale": "...", "citations": [] },
    "runoff": { "support": 0.13, "confidence": 0.64, "rationale": "...", "citations": [] },
    "physical": { "support": 0.05, "confidence": 0.78, "rationale": "...", "citations": [] }
  },
  "dominant_causes": ["thermal", "disease"],
  "ambiguity": 0.72,
  "lowest_confidence": 0.64,
  "coordinator": {
    "evidence_sufficient": false,
    "additional_evidence_needed": true,
    "next_evidence": [
      {
        "type": "close_range_lesion_image",
        "priority": 1,
        "rationale": "Thermal and disease are both well supported and imply different actions."
      }
    ],
    "reasoning_summary": "..."
  }
}
```

Note what this response does **not** contain: a winning cause, a diagnosis, or a normalized distribution.
`dominant_causes` is a list because more than one cause can be in play.

The four `support` values will not sum to 1.
That is correct, not a bug, and the frontend must not render them as parts of a whole.

### `GET /plan/current`

The current response plan.

```json
{
  "plan_id": "plan_20260817_1402",
  "generated_at": "2026-08-17T14:02:14Z",
  "scenario_id": "demo_default",
  "scenario_banner": "Simulated operational capacity. Not a real organization's fleet or personnel data.",
  "assignments": [
    {
      "site_id": "sombrero",
      "site_name": "Sombrero Reef",
      "action_id": "intensive_monitoring",
      "action_class": "monitoring",
      "boat_id": "boat_a",
      "team_id": "team_1",
      "priority": "high",
      "estimated_hours": 3.0,
      "estimated_cost_usd": 800.0,
      "evidence_summary": "Thermal support 0.82 at confidence 0.91.",
      "remaining_uncertainty": "Disease support 0.61 is unresolved pending lesion imagery.",
      "compatibility_rationale": "Monitoring is eligible for all four causes and carries no contraindications here.",
      "requires_manager_approval": true
    }
  ],
  "deferred": [
    {
      "site_id": "looe_key",
      "site_name": "Looe Key",
      "fallback_action_id": "intensive_monitoring",
      "reason": "Intervention deferred because both boats are committed for the full operating day."
    }
  ],
  "total_strategic_value": 1.94,
  "binding_constraints": ["boat_hours", "monitoring_kits"],
  "replan_trigger": null,
  "replan_latency_ms": null
}
```

`scenario_banner` rides on the plan itself rather than being looked up separately, so it cannot be dropped in the UI.

`binding_constraints` is what lets the dashboard explain a trade-off rather than just presenting a result.
The optimizer derives these by re-solving with the smallest capacity relaxations that improve the objective.
It does not require a resource counter to land at exact numeric saturation.
Each deferred site also receives plain-language trade-off text rather than raw constraint keys.

### `POST /observations`

Submit a field report.
This is the demo's re-planning trigger.

Request:

```json
{
  "site_id": "cheeca_rocks",
  "observed_at": "2026-08-17T14:05:00Z",
  "observer": "Dive Team B",
  "text": "Cheeca Rocks now shows localized tissue loss with visible lesions.",
  "image_refs": []
}
```

Response:

```json
{
  "report_id": "rpt_0007",
  "accepted_at": "2026-08-17T14:05:01Z",
  "structured": { "...": "StructuredObservation" },
  "replan": { "plan_id": "plan_20260817_1405", "latency_ms": 4180 }
}
```

Returning the latency here is what lets the dashboard display responsiveness without measuring it client-side, which would include network noise.

### `GET /resources/scenario` and `PATCH /resources/scenario`

The active simulated capacity, and the controls that change it.

```json
{
  "scenario_id": "demo_default",
  "label": "Demo scenario: two boats, three dive teams, one operating day",
  "provenance": "simulated",
  "banner": "Simulated operational capacity. Not a real organization's fleet or personnel data.",
  "boats": [{ "boat_id": "boat_a", "name": "Boat A", "available": true, "operational_hours": 7.0 }],
  "dive_teams": [{ "team_id": "team_1", "name": "Dive Team A", "diver_count": 4, "available_hours": 6.0 }],
  "inventory": { "shade_units": 4, "monitoring_kits": 3, "sampling_kits": 2 },
  "budget_usd": 10000.0,
  "daylight_hours": 7.0
}
```

`PATCH` accepts a partial update, for example marking Boat B unavailable, and returns the same body plus a `replan` block.
This is demo beat five.

### `POST /plan/recompute`

Force a recompute. Returns the new plan and its latency.
Useful for the demo and for debugging; not part of the normal loop.

### `GET /plan/{plan_id}/trace`

Returns the ordered, structured execution trace for one completed plan.
The response carries a unique `trace_id`, plan ID, and success status.
Each step identifies its site, stage, executor, timing, redacted inputs, validated output, concise rationale, and validation checks.
Live LLM steps also carry provider, model, attempt count, and provider-reported token usage when available.

The trace includes evidence tools, four investigators, deterministic fusion, policy eligibility, the Coordinator decision, and the optimizer result.
A resource-only replan contains only an optimizer step and links to its parent plan because unchanged investigators must not rerun.

The trace never exposes API keys, authorization headers, raw prompts, or private token-by-token model reasoning.
Large inputs are referenced by stable site, report, snapshot, scenario, and action IDs instead of being copied into every stage.

### `GET /plan/failed-traces/{trace_id}`

Returns a bounded failed-run trace after an exception reports its trace ID.
The failed step contains status, error type, a redacted error message, timing, and the inputs available at that boundary.
Only the eight most recent failed traces and the 32 most recent completed plan states are retained by the in-process prototype.

### `GET /plan/{plan_id}/trace/{site_id}`

Returns the site-specific stages from the same trace plus plan-wide stages such as the optimizer.
This is the dashboard-facing view for explaining one site's evidence and resulting allocation.

### `GET /evaluation`

The evaluation results, reported per module.

```json
{
  "thermal": {
    "metric": "IoU vs NOAA Bleaching Alert Area",
    "value": 0.94,
    "scope": "thermal-evidence module output only, before fusion",
    "caveat": "Consistent with NOAA's own designation. Bleaching Alert Area is not an independently verified ground truth."
  },
  "disease": { "metric": "...", "value": null, "caveat": "..." },
  "runoff": { "metric": "...", "value": null, "caveat": "..." },
  "physical": { "metric": "...", "value": null, "caveat": "..." },
  "optimizer": {
    "baseline_strategic_value": 1.42,
    "optimized_strategic_value": 1.94,
    "difference_pct": 36.6,
    "caveat": "Compares two policies inside the same defined problem. Makes no claim about the real ocean."
  }
}
```

There is deliberately no combined accuracy number.
Rolling the four modules together would recreate the fused-versus-single-cause mismatch the evaluation design exists to avoid.

Each caveat ships next to its number so the UI cannot present the number alone.

## Errors

Standard HTTP status codes with a JSON body:

```json
{ "detail": "Human-readable message", "code": "machine_readable_code" }
```

A Coordinator business-rule violation is a server error, not a client error, and it is logged loudly.
It means the model produced something the pipeline correctly refused, which is the safety mechanism working.

## Versioning

No versioning for the prototype.
The contract changes by agreement between the two tracks, and the OpenAPI schema is the source of truth for the generated types.
