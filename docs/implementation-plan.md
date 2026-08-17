# Implementation plan

The work is split into small tasks with explicit dependencies.
The order is intentional: data foundation first, Data and Agents plus Backend in parallel, and Frontend last.

The shared target is one reliable offline demo loop.

```text
data contract and fixtures
    -> data and backend work in parallel
    -> typed API fixtures
    -> dashboard
```

## Track 1: Data foundation and curation

This track makes the demo inputs trustworthy and reproducible.
It does not mean every real external integration must be finished before backend work starts.
The minimal contract and fixture set are the first dependency.

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| DATA-01 | Define the fixture and provenance format | none | Every demo value can be labeled live, cache, simulated, or synthetic. |
| DATA-02 | Complete the seven site records | DATA-01 | Coordinates, measurements, source notes, and restoration fields validate without placeholders. |
| DATA-03 | Complete the simulated resource scenario | DATA-01 | Boats, teams, inventory, budget, daylight, and the simulated banner load from YAML. |
| DATA-04 | Complete the intervention catalog citations | DATA-01 | Every catalog action has usable provenance and required policy fields. |
| DATA-05 | Implement the local cache read/write layer | DATA-01 | Cached snapshots round-trip with timestamps and source metadata. |
| DATA-06 | Implement synthetic demo reports and structuring fixtures | DATA-01 | Initial reports and the Cheeca Rocks update load deterministically. |
| DATA-07 | Implement NOAA and AGRRA snapshot adapters | DATA-05 | Prefetch can populate cache, and forced-cache mode never calls the network. This does not block the offline backend slice. |
| DATA-08 | Add data validation and a repeatable fixture check | DATA-02, DATA-03, DATA-04, DATA-05, DATA-06 | One command proves the demo inputs are complete and honestly labeled. |

Data track handoff: the backend can load sites, scenario, catalog, cached signals, and demo reports without network access.
The real NOAA and AGRRA adapters can finish after the fixture-backed backend path exists.

## Track 2: Agents plus Backend

This track turns the minimal data foundation into a deterministic, testable decision pipeline.
It can start as soon as DATA-01 and the relevant fixture contracts are stable.
The LLM remains behind a stub or fixture implementation until the deterministic path works.

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| BACK-01 | Implement site score calculation | DATA-02 | Ecological and strategic values are separate and tested. |
| BACK-02 | Implement deterministic thermal evidence | DATA-01 | DHW and HotSpot fixtures produce documented alert and support behavior. |
| BACK-03 | Implement fixture-backed disease, runoff, and physical evidence | DATA-06 | All four causes return support, confidence, rationale, citations, and provenance. |
| BACK-04 | Implement evidence fusion | BACK-02, BACK-03 | Dominant causes, ambiguity, and lowest confidence are deterministic and tested. |
| BACK-05 | Implement policy catalog loading and eligibility | DATA-04, BACK-04 | Only source-backed, condition-compatible actions reach the Coordinator. |
| AGENT-01 | Implement Coordinator prompt and fixture decisions | BACK-04, BACK-05 | Ambiguous cases request named evidence; clear cases approve only eligible actions. |
| AGENT-02 | Implement Coordinator business-rule validation | AGENT-01, BACK-05 | Unknown, incomplete, or contraindicated actions fail loudly. |
| BACK-06 | Implement allocation model and site scoring inputs | BACK-01, AGENT-02, DATA-03 | The optimizer receives typed candidates and resources only. |
| BACK-07 | Implement OR-Tools solve and baseline solve | BACK-06 | Plans obey capacity, expose binding constraints, and report deferred sites. |
| BACK-08 | Implement the full pipeline entry point | BACK-02, BACK-03, BACK-04, BACK-05, BACK-07 | `pipeline.run()` returns a valid `ResponsePlan` from the demo fixtures. |
| BACK-09 | Implement re-planning for new evidence and resource changes | BACK-08 | The Cheeca report and Boat B outage produce changed plans with latency. |
| BACK-10 | Implement API state and routes | BACK-08, BACK-09 | The real API serves health, sites, evidence, resources, observations, and current plan. |
| BACK-11 | Unskip and complete integration and end-to-end tests | BACK-10 | The closed loop passes through the real API path with no skipped tests. |
| AGENT-03 | Choose and integrate the Coordinator LLM client | AGENT-02, ADR-005 | Live structured output is optional, bounded, retryable, and fully stubbed in tests. |

Agents plus Backend handoff: the API serves a complete offline plan and can re-plan after evidence or capacity changes.

## Track 3: Frontend

Frontend work starts after BACK-10 provides stable API responses or fixtures matching the same OpenAPI schema.

| ID | Task | Depends on | Done when |
| --- | --- | --- | --- |
| UI-01 | Generate or verify API types from OpenAPI | BACK-10 | Frontend types match backend response fields and enum values. |
| UI-02 | Build the page shell and simulated-data banner | UI-01 | The page clearly states the operational-data provenance. |
| UI-03 | Build the current plan surface | UI-02 | Assignments, priorities, manager approval, rationale, uncertainty, and deferrals are visible. |
| UI-04 | Build the evidence surface | UI-03 | Four independent support bars show confidence and citations without implying probabilities. |
| UI-05 | Build resource controls and re-plan feedback | UI-03, BACK-09 | A resource change visibly triggers and explains a new plan. |
| UI-06 | Build evaluation surface | UI-03 | Thermal, disease, runoff, physical, optimizer, and latency results remain separate. |
| UI-07 | Run responsive and accessibility QA against the demo flow | UI-02, UI-03, UI-04, UI-05, UI-06 | Loading, empty, error, focus, contrast, and responsive states are checked at demo resolution. |

## Execution rules

- Finish DATA-01 before parallel implementation begins.
- Use labeled fixture data to unblock backend work; real external curation is a hardening task, not the first blocker.
- Finish DATA-02, DATA-03, DATA-04, and DATA-06 before the offline plan handoff.
- Finish DATA-05 and DATA-07 before claiming the external-data path is demo-ready.
- Finish BACK-08 before polishing the dashboard.
- Keep the first Coordinator implementation deterministic and fixture-backed.
- Do not make the frontend invent fields that are absent from the API contract.
- Each task should have one focused commit and a verification command.
- A task is not complete if it only makes the happy-path output look right while provenance, uncertainty, or constraints are missing.

## First milestone

The first milestone is DATA-01 plus the minimal fixture tasks DATA-02, DATA-03, DATA-04, and DATA-06, together with BACK-01 through BACK-08.
Its acceptance test is a cached `GET /plan/current` response containing a valid `ResponsePlan`, the simulated-data banner, provenance, assignments or deferrals, and binding constraints.
