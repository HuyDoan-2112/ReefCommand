# ReefCommand: project context

This file is the whole context of the project.
Read it before doing anything here.
Working rules live separately in `AGENTS.md` and `.agents/rules/`.

## What this is

An AI decision-support system that turns environmental monitoring, field observations, scientific intervention guidance, and limited conservation resources into continuously updated reef-response plans.

The one-line insight the whole product rests on:

> Reef managers do not have a lack-of-data problem.
> They have a decision-under-resource-constraints problem.

## What this is not

Do not describe ReefCommand as any of these, in code comments, in the dashboard, or in the pitch:

- "an AI that saves coral reefs"
- "an autonomous coral treatment system"
- "a coral disease diagnosis model"
- "another NOAA dashboard"
- "five AI agents working together"

It is not a replacement for NOAA.
It is not primarily a bleaching-detection system.
It is not a chatbot.

## The problem, stated properly

Reef managers already have substantial monitoring information.
That information does not tell them what to do today with the resources they actually have.

There are two disconnected layers.

**Satellite and environmental monitoring.**
NOAA Coral Reef Watch provides Degree Heating Weeks, Coral Bleaching HotSpot, Bleaching Alert Area, sea-surface temperature, and bleaching outlook products.
This is good for thermal stress across broad areas.
It cannot distinguish why an individual reef is deteriorating: thermal stress, disease, runoff, physical damage, or several at once.

**Field observations.**
Divers, scientists, restoration teams, and citizen scientists see paling, bleaching percentage, tissue loss, lesion patterns, broken coral, turbidity, sediment, and change since the last dive.
These are highly local and highly valuable, and they arrive as unstructured prose:

> "The western section looks much worse than last week.
> A lot of the branching coral is pale and there are several colonies with what looks like tissue loss."

A deterministic pipeline cannot reliably interpret every possible natural-language field report.
That is one of the two places an LLM earns its place here.

**The gap.**
Given environmental signals, local field observations, scientific intervention guidance, and the limited resources available today, which reef sites should managers prioritize and what response is appropriate?

A manager may face five stressed sites with two boats, three dive teams, four shade units, three monitoring kits, seven hours of daylight, and ten thousand dollars.
They cannot respond equally to every site.
ReefCommand is therefore a decision-support and resource-allocation system.

## Why causal evidence matters

Ranking reefs by thermal stress alone is not enough.

| Site | Signal | Plausible cause |
| --- | --- | --- |
| A | High DHW, widespread paling | Thermal stress |
| B | Moderate DHW, localized tissue loss, nearby disease reports | Disease |
| C | Low DHW, broken branching coral right after a storm | Physical damage |

All three look damaged.
The useful response differs.
So the system maintains four competing evidence categories: thermal, disease, runoff, physical.

**These are not mutually exclusive.**

```text
Thermal:   0.82
Disease:   0.58
Runoff:    0.11
Physical:  0.04
```

These are `evidence_support_scores`, not probabilities.
They are not normalized to sum to 1, and the four causes are not assumed statistically independent.
That overlap is the point: thermal and disease can both be well supported at once.

Only call a value `P(cause | evidence)` once a probabilistic model has actually been calibrated against expert-labeled cases.
Until then the field name stays `support`.

## Architecture

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
                 Evidence fusion            (deterministic)
                       |
             Intervention policy engine     (deterministic)
                       |
                  Coordinator agent         (the only autonomous component)
                 "Act or get more data?"
                       |
                    Optimizer               (deterministic, OR-Tools)
                       |
          Boats + teams + gear + time
                       |
                   ACTION PLAN
```

### Where an LLM is used, and where it is not

Use an LLM only where it adds clear value.

| Stage | Implementation | Why |
| --- | --- | --- |
| Data intake | Deterministic | Fetching, caching, and retaining raw reports. Nothing to reason about. |
| Report structuring | LLM, schema-constrained | Converts messy field prose into optional observation fields without diagnosing or inventing missing values. |
| Thermal evidence | Deterministic | Reading DHW and applying documented thresholds is numeric comparison. Do not use an LLM to compare numbers. |
| Disease evidence | LLM plus tools | Lesions, tissue loss, affected species, spatial progression, disease-like morphology. Requires interpretation. |
| Runoff evidence | LLM plus tools | Diver descriptions, rainfall, turbidity, geography, proximity to runoff sources. |
| Physical evidence | LLM plus tools | Breakage reports, storm history, wave data, vessel and anchor activity. |
| Evidence fusion | Deterministic | Aggregates four support scores into one summary. No LLM call. |
| Policy engine | Deterministic | The model does not decide what treatments exist. |
| Coordinator | LLM, schema-constrained | Decides: act now, or get more data. |
| Optimizer | Deterministic, OR-Tools | Resource allocation is a constrained optimization problem. |

### The disease investigator's grounded tool

Query the AGRRA Caribbean Coral Health Watch / SCTLD Tracking Map at `agrra.org/coral-disease-outbreak` for reviewed disease and bleaching reports near the site.
This is a real, specific tool, not a generic placeholder.

Preserve each record's source metadata: submission date, review status, reporting organization.
Do not discard it after the lookup.

Geographic proximity to a reviewed record is supporting evidence, not confirmation.
Proximity alone never proves a new field report is SCTLD.
It feeds the disease support score alongside the lesion description, never as a binary override.

Describe the map as AGRRA's reviewed regional tracker.
Do not assert that all Florida records come specifically from FWC's Fish and Wildlife Research Institute.
NOAA references the AGRRA map in its own SCTLD implementation planning.

## The Coordinator

The Coordinator is the main autonomous reasoning component and the only truly autonomous one.
Everything upstream and downstream of it is deterministic.

Its purpose is not "pick whichever hypothesis has the largest score".
Its purpose is to determine what should happen next when the evidence is incomplete or conflicting.

```text
Thermal = 0.91, Disease = 0.17   ->  evidence likely sufficient, proceed
Thermal = 0.68, Disease = 0.65   ->  ambiguous, and the causes imply different
                                     actions, so request close-range lesion imagery
```

The workflow is therefore dynamic:

```text
fusion -> policy -> coordinator approves -> optimizer

fusion -> policy -> coordinator finds evidence insufficient
       -> requests another observation
       -> fusion updates -> policy re-evaluates -> reconsider
```

That changing execution path is the justification for an autonomous agent at this one point, and nowhere else.

### The reliability rule

The Coordinator must never send free-form prose into the optimizer.

```text
Evidence fusion
      |
Intervention Policy Engine
      |
Coordinator LLM
      |
Schema-constrained structured output
      |
Pydantic / JSON Schema validation
      |
business-rule validation
      |
Optimizer
```

The optimizer should never have to parse a sentence like "thermal stress seems pretty likely, so maybe try shading".
It receives validated objects:

```json
{
  "site_id": "sombrero",
  "evidence_support_scores": {
    "thermal":  { "support": 0.82, "confidence": 0.91 },
    "disease":  { "support": 0.61, "confidence": 0.73 },
    "runoff":   { "support": 0.13, "confidence": 0.64 },
    "physical": { "support": 0.05, "confidence": 0.78 }
  },
  "evidence_sufficient": false,
  "additional_evidence_needed": true,
  "next_evidence": [{ "type": "close_range_lesion_image", "priority": 1 }]
}
```

Malformed or incomplete output fails validation instead of propagating downstream.

The `evidence_support_scores` arrive from evidence fusion.
The eligible actions arrive from the policy engine.
The Coordinator computes neither. It reasons over both.

## The LLM must not invent interventions

The system maintains a source-grounded intervention knowledge base and policy engine.
It maps evidence and conditions to allowed candidate actions.

Candidate classes: monitoring, targeted disease survey, biosecurity workflow, water-quality investigation, physical-damage assessment, and temporary shading where the knowledge base's requirements and contraindications for that specific site are met.

Every action carries: applicable hypothesis, evidence strength, requirements, contraindications, resource requirements, expected compatibility, and provenance.

**On shading specifically.**
Effectiveness is context-specific, not a given.
A peer-reviewed field study found no measurable shading benefit at two coral nursery sites.
That is exactly why every action needs requirements, contraindications, and provenance rather than being treated as a generic fix.

Interventions here are source-backed, policy-eligible candidate actions requiring manager approval.
They are not blanket "scientifically valid" prescriptions.
Eligibility means grounded in a cited source and applicable to the evidence pattern.
It does not mean guaranteed to work.

Division of labor:

- The **policy engine** determines what is policy-eligible and source-backed, before the Coordinator sees the case.
- The **Coordinator** reasons about which already-eligible actions the current evidence supports acting on now.
- The **optimizer** determines which approved actions are feasible given resources.

## The optimizer

The operational problem is resource scarcity.
Example capacity: 2 boats, 3 dive teams, 4 shade units, 3 monitoring kits, ten thousand dollars, 7 hours of daylight.

With five sites needing attention, the system cannot just say "these five are important".
It must answer: given available resources, what combination of actions produces the greatest expected strategic value?

Allocation is deterministic and solved with a constrained optimizer such as OR-Tools.
The LLM must not directly assign boats or teams.

## Data rules

**Environmental data.** Real NOAA data where practical.
**Field observations.** Realistic synthetic or demo reports unless real suitable reports are available.
**Operational resources.** Clearly labeled simulated management scenarios.

Do not pretend simulated resource data are real.
The architecture should allow simulated inputs to be replaced later by an organization's actual operational systems.

## Study area

The seven Florida Keys sites associated with NOAA Mission: Iconic Reefs.

Do not claim NOAA ranks these sites from most to least ecologically valuable.
NOAA confirms they are ecologically and culturally significant.
It does not numerically rank them.

**CREMP correspondence is not exact.**
FWC's Coral Reef Evaluation and Monitoring Project provides coral cover, condition, abundance, and diversity data, including downloadable site-level data.
But CREMP monitors roughly 40 sites across the Florida Keys while Mission: Iconic Reefs covers seven specific restoration sites.
They are not a 1:1 mapping.

Use CREMP measurements only where an Iconic Reefs site has suitable spatial and habitat correspondence to a CREMP station.
Document the distance, habitat type, and matching method used.
Where no suitable coverage exists, use another cited source or a clearly labeled synthetic placeholder.
Never substitute silently.

## Two scores, not one blended number

Restoration investment is a management consideration, not an ecological one.
Blending them into a single `conservation_value` quietly mixes two different kinds of judgment.

```text
ecological_value(site) = 0.6 * normalized(coral_cover)
                       + 0.4 * normalized(species_richness)

strategic_value(site)  = 0.7 * ecological_value(site)
                       + 0.3 * normalized(restoration_investment)
```

- `coral_cover` and `species_richness` come from CREMP where correspondence is documented, otherwise a labeled placeholder.
- `restoration_investment` flags whether the site has active nursery or outplant work. This is prior management commitment, not ecological value, which is why it lives only in `strategic_value`.
- Do not cite specific organizations' investment at specific sites unless verified per site. An unverified claim here is worse than no claim.

The weights (0.6/0.4 and 0.7/0.3) are stated prototype assumptions, not scientific claims.
Say so explicitly on the dashboard and in the pitch.

The optimizer is wired to `strategic_value`.
`ecological_value` stays on the dashboard as the more defensible, investment-agnostic number for when someone asks what the reef actually needs independent of what has already been spent there.

## What the output looks like

An operations plan, not an AI answer.

```text
CURRENT RESPONSE PLAN

Boat A + Dive Team 1
-> Sombrero Reef
-> intensive monitoring
-> priority: high

Boat B + Dive Team 2
-> Cheeca Rocks
-> targeted disease assessment
-> priority: high

Looe Key
-> monitoring only
-> intervention deferred because of capacity constraints
```

The dashboard must also explain what evidence supported the decision, what uncertainty remains, what resource constraints caused the trade-offs, and why an intervention was considered compatible.

## Continuous re-planning

The strongest demonstration is not the initial recommendation.
It is what happens when reality changes.

**New evidence.** A diver submits "Cheeca Rocks now shows localized tissue loss with visible lesions." Evidence changes, the Coordinator reevaluates, the optimizer may produce a new allocation.

**Resource change.** Boat B becomes unavailable. The existing plan may become infeasible, and the system detects that and recomputes without being asked.

```text
OBSERVE -> STRUCTURE -> INVESTIGATE -> FUSE EVIDENCE
    -> CONSTRAIN TO POLICY-ELIGIBLE ACTIONS
    -> REASON ABOUT UNCERTAINTY -> OPTIMIZE
    -> ACT / DISPLAY PLAN -> NEW INFORMATION -> repeat
```

## Demo reliability

Live external APIs are a demo liability, not a feature.

- Pre-fetch and cache NOAA ERDDAP DHW data for the study area and replay window before the event. Never depend on a live NOAA call during a live presentation.
- Any live call kept for effect gets a short timeout, around 3 seconds, with automatic fallback to cache. The audience should never see a spinner or an error.
- Cache an AGRRA snapshot ahead of time through a permitted export or a curated snapshot. Do not assume the dashboard allows unrestricted automated scraping.
- Log which values came from a live call versus cache, so the team can honestly answer "is this live right now".

## Evaluation

Do not claim ReefCommand "saves coral". That is not measurable here.
Full methodology in `docs/evaluation.md`. In short:

**A. Thermal-evidence check.** IoU between the thermal-evidence module output only, before fusion, and NOAA's Bleaching Alert Area.
Never compare the fused four-cause score against Bleaching Alert Area, which represents heat-stress bleaching risk only.
That mismatch would produce a misleading number.
Expect a high IoU, because both sides compute the same DHW logic. It is a pipeline-correctness check, not a novel scientific claim.

Say "consistent with NOAA's own designation", not "proven correct".
NOAA's methodology notes the field observations behind the 4 and 8 degree C-week thresholds were informal reports "not calibrated/validated with corresponding satellite data", and NOAA states it does not conduct its own in-water surveys.
That is a point in our favor: NOAA's product depends on structured field reports to stay accurate, and this system captures and fuses them systematically instead of by ad hoc email.

**Per-module checks, reported separately.** Disease against AGRRA records, runoff against the rainfall and turbidity input, physical against storm and vessel records.
Never roll them into one combined accuracy number.

**B. Optimizer versus a naive baseline.** Follows systematic conservation planning (Margules and Pressey, Nature, 2000; Marxan comparisons such as PMC7261139 report 12 to 30 percent gaps).
Hold resources fixed, compare first-reported-or-highest-DHW against the optimized allocation, report total `strategic_value` protected under each.
This compares two policies inside one defined problem and claims nothing about the real ocean.

**C. Re-planning responsiveness.** Time or step count from evidence submitted to updated plan displayed. Show it live.

## Human role

The system is decision support.
A human reef manager remains responsible for approving operational actions.

ReefCommand prioritizes, explains, surfaces uncertainty, requests more evidence, optimizes resources, and shows trade-offs.
It does not claim final scientific or operational authority.

## Objective

This is a prototype, not a production system.
The goal is one convincing closed loop:

```text
real environmental signal + field observation
    -> evidence changes
    -> source-backed, policy-eligible candidate actions requiring manager approval
    -> agent handles uncertainty (act now, or get more data?)
    -> optimizer allocates limited resources
    -> dashboard updates
    -> new event occurs
    -> system re-plans
```

A reliable three-minute end-to-end demonstration matters more than implementing every possible data integration.
If a feature does not strengthen this closed loop, treat it as secondary.

## Build plan

Work is split into small tasks in `docs/implementation-plan.md`.
The dependency order is:

1. Minimal data contract and reproducible fixtures.
2. Data curation and Agents plus Backend in parallel.
3. Frontend after stable API fixtures.

Data tasks produce reproducible, honestly labeled fixtures and cached signals.
Agents plus Backend tasks can use those fixtures while real NOAA and AGRRA adapters are still being hardened.
Frontend tasks start only after the API serves fixtures matching its OpenAPI contract.

The first milestone is a cached `GET /plan/current` response containing a valid `ResponsePlan`, provenance, the simulated-data banner, assignments or deferrals, and binding constraints.
Exhaustive real-data curation, live external services, live LLM calls, and dashboard polish are later milestones.

## Repository map

```text
AGENTS.md            General working rules. Read with this file.
.agents/rules/       Commit rules, code rules, multi-agent rules.
.agents/teammates/   Data, Agents plus Backend, and Frontend track briefs.
docs/                Architecture, data sources, evaluation, demo runbook,
                     tech decisions, API requirements, implementation plan.
backend/             Python pipeline and API. One package per pipeline stage.
frontend/            Dashboard.
scripts/             Cache prefetch, demo seeding.
```

See `docs/architecture.md` for the package-level view and `docs/tech-decisions.md` for why each technology was chosen.
