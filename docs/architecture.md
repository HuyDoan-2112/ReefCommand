# Architecture

## Principle

Use an LLM only where it adds clear value.
Everything that can be a documented rule stays a documented rule.

| Stage | Implementation | Why |
| --- | --- | --- |
| Ingestion | Deterministic adapters | Fetching and caching, nothing to reason about. |
| Thermal evidence | Deterministic | Reading DHW and HotSpot and applying documented thresholds is numeric comparison. Do not use an LLM for this. |
| Disease evidence | LLM plus tools | Field text describes lesions, tissue loss, spatial progression. Requires interpretation. |
| Runoff evidence | LLM plus tools | Combines diver text, rainfall, turbidity, geographic context. |
| Physical evidence | LLM plus tools | Combines breakage reports, storm history, vessel and anchor activity. |
| Evidence fusion | Deterministic | Aggregates the four support scores into one reconciled summary. No LLM call. |
| Policy engine | Deterministic | The model does not decide what treatments exist. |
| Coordinator | LLM, schema-constrained | The only autonomous component. Decides act now versus get more data. |
| Optimizer | Deterministic, OR-Tools | Resource allocation is a constrained optimization problem. |

## Data flow

```text
NOAA data --------+
                  |
Diver reports ----+--> Current reef state
                  |
Reef/site data ---+
                       |
            Four competing hypotheses
     thermal | disease | runoff | physical
                       |
                 Evidence fusion
                       |
             Intervention policy engine
                       |
                  Coordinator agent
                 "Act or get more data?"
                       |
                    Optimizer
                       |
          Boats + teams + gear + time
                       |
                   ACTION PLAN
```

## The four hypotheses are not mutually exclusive

Each investigator produces an independent support score with its own confidence.
Scores are not normalized against each other and the causes are not assumed statistically independent.
Thermal stress and disease can both be well supported at the same site at the same time, and often are.

Only call a value `P(cause | evidence)` if a probabilistic model has actually been calibrated against expert-labeled cases.
Until then the field name stays `support`.

## The Coordinator contract

The Coordinator sees, as input:

1. The fused evidence summary produced by `evidence/fusion.py`.
2. The list of already-eligible candidate actions produced by `policy/engine.py`, each with its evidence requirements.

It does not compute either of those itself.
Its question is never "which hypothesis wins" but "is the current evidence sufficient to act on one of these eligible actions, or do we need another observation first".

Its output passes through, in order:

```text
Coordinator LLM
   |
schema-constrained structured output
   |
Pydantic / JSON Schema validation
   |
business-rule validation
   |
Optimizer
```

Malformed or incomplete output fails validation and is not propagated.
The optimizer must never have to parse a sentence.

## Re-planning

The pipeline is re-entrant.
Two triggers cause a recompute:

- New evidence, for example a diver report of localized tissue loss at a site previously assessed as thermal only.
- Resource change, for example a boat becoming unavailable, which can make the current plan infeasible.

`orchestration/replanner.py` owns detecting these and re-running only the stages that need re-running.
Time from evidence submitted to updated plan displayed is a reported metric, not an implementation detail.
