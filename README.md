# ReefCommand

An AI decision-support system that turns environmental monitoring, field observations, scientific intervention guidance, and limited conservation resources into continuously updated reef-response plans.

Reef managers do not have a lack-of-data problem.
They have a decision-under-resource-constraints problem.

ReefCommand is a prototype.
It is decision support: a human reef manager remains responsible for approving every operational action.

## What it is not

It is not a replacement for NOAA Coral Reef Watch.
It is not a bleaching-detection system, a coral disease diagnosis model, a coral chatbot, or an autonomous coral treatment system.

## The closed loop

```text
OBSERVE
   |
STRUCTURE
   |
INVESTIGATE          (four competing, non-exclusive causes)
   |
FUSE EVIDENCE        (deterministic)
   |
CONSTRAIN TO POLICY-ELIGIBLE ACTIONS   (deterministic policy engine)
   |
REASON ABOUT UNCERTAINTY               (Coordinator: act now, or get more data?)
   |
OPTIMIZE             (deterministic, OR-Tools)
   |
ACT / DISPLAY PLAN
   |
NEW INFORMATION
   `--> back to OBSERVE
```

The Coordinator is the only autonomous component.
Everything upstream and downstream of it is deterministic.
The Coordinator never emits free-form prose into the optimizer: its output is schema-constrained, validated by Pydantic, then validated again against business rules.

## Repository layout

```text
ReefCommand/
  AGENT.md                  Working rules for AI agents. Read this first.
  CLAUDE.md                 Imports AGENT.md plus a short checklist.
  tasks.ps1                 Task runner. Run `.\tasks.ps1 help`.
  docs/                     Architecture, data sources, evaluation, demo runbook.
  scripts/                  Operational scripts (cache prefetch, demo seeding).
  backend/                  Python pipeline and API.
    src/reefcommand/
      domain/               Pydantic models shared by every stage.
      ingestion/            External data adapters plus the cache layer.
      evidence/             Four cause investigators plus deterministic fusion.
      policy/               Source-grounded intervention knowledge base and engine.
      coordinator/          The single autonomous agent, its schema and validation.
      optimizer/            Constrained resource allocation (OR-Tools).
      orchestration/        Pipeline wiring, event handling, re-planning.
      api/                  FastAPI application and routes.
      llm/                  Model client and structured-output plumbing.
      data/                 Site definitions, demo scenarios, cached snapshots.
    tests/                  unit / integration / e2e.
  frontend/                 Vite + React + TypeScript dashboard.
    src/features/           One folder per dashboard surface.
```

## Getting started

### Backend

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn reefcommand.api.app:app --reload
```

Lint, format, and test:

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

### Frontend

Requires Node 20 or newer.

```bash
cd frontend
npm install
npm run dev
```

### Task runner

`tasks.ps1` wraps the common commands on Windows.

```powershell
.\tasks.ps1 setup
.\tasks.ps1 api
.\tasks.ps1 check
```

Run `.\tasks.ps1 help` for the full list.
On macOS or Linux, run the underlying commands directly.

### Environment

Copy `.env.example` to `.env` and fill in the values.
Never commit `.env`.

## Data honesty rules

These are load-bearing, not decoration.

- Environmental data uses real NOAA Coral Reef Watch products where practical, pre-fetched and cached before any demo.
- Field observations are realistic synthetic or demo reports unless real suitable reports are available.
- Operational resources (boats, teams, inventory, budget) are clearly labeled simulated management scenarios. They are never presented as real.
- Every displayed value records whether it came from a live call or from cache.
- `evidence_support_scores` are support scores, not probabilities. They are not normalized to sum to 1 and the four causes are not assumed independent.
- Scoring weights are stated prototype assumptions, not scientific claims, and are labeled as such on the dashboard.

## Two scores, not one

```text
ecological_value(site) = 0.6 * normalized(coral_cover)
                       + 0.4 * normalized(species_richness)

strategic_value(site)  = 0.7 * ecological_value(site)
                       + 0.3 * normalized(restoration_investment)
```

The optimizer is wired to `strategic_value`.
`ecological_value` stays on the dashboard as the investment-agnostic number.

## Evaluation

See `docs/evaluation.md`.
Each evidence module is evaluated separately against evidence relevant to that module.
The fused compound score is never compared against NOAA Bleaching Alert Area, because that product represents heat-stress-related bleaching risk only.

## License

TBD.
