# Tech decisions

Short architecture decision records.
Each one says what was decided, what else was considered, and why.

Status values: **Accepted** (in the code now), **Proposed** (needs a call before the relevant issue starts), **Rejected**.

When you disagree with one, change it here in its own pull request with the reasoning.
Do not just do something different in code and leave this stale.

---

## ADR-001: Python for the pipeline

**Status:** Accepted

Every non-UI part of this system is scientific or combinatorial: reading NOAA grid products, computing degree heating weeks, constrained allocation, statistical checks.
That work has a mature Python ecosystem and a thin one everywhere else.
OR-Tools, xarray, netCDF4, and pandas are all first-class in Python.

Python 3.12 or newer, so PEP 695 type parameters and `StrEnum` are available.

---

## ADR-002: FastAPI for the API

**Status:** Accepted

We need an OpenAPI schema, because the frontend generates its types from it.
FastAPI produces that schema directly from the same Pydantic models the pipeline already uses, so there is one definition of a response shape rather than two that drift.

Considered: Flask (no schema generation, no async), Django (far too much for six endpoints), Litestar (fine, smaller ecosystem, no reason to prefer it here).

---

## ADR-003: Pydantic v2 as the contract between stages

**Status:** Accepted

The reliability argument for this architecture is that Coordinator output cannot reach the optimizer unvalidated.
That argument only holds if validation is real, and Pydantic is how it is real.

Frozen models by default.
Schema-level invariants live on the model, cross-object rules live in `coordinator/validation.py`.

This also means the agent framework we pick should speak Pydantic natively rather than making us convert in and out of it.

---

## ADR-004: OR-Tools for allocation

**Status:** Accepted

Boats, dive teams, gear, budget, and daylight against a set of candidate actions is a constrained optimization problem with integer decisions.
CP-SAT handles it directly and gives us the binding constraints back, which the dashboard needs in order to explain trade-offs.

Considered: a greedy heuristic (cheaper, but then the evaluation in `docs/evaluation.md` has nothing meaningful to compare against, since the greedy version *is* the baseline), PuLP or a MILP solver (workable, CP-SAT expresses the scheduling constraints more naturally).

---

## ADR-005: Agent framework for the Coordinator

**Status:** Proposed. Decide before `[agents] LLM client with schema-constrained output` starts.

### What we actually need

This is the decision worth being careful about, because the obvious answer is probably wrong for this system.

The system has **one** autonomous component.
The Coordinator receives fused evidence and a pre-computed list of eligible actions, and returns a validated object.
It may request one additional observation, which re-enters the pipeline through deterministic orchestration rather than through an autonomous loop.

So the requirement is narrow:

- reliable structured output against a Pydantic model
- a small, bounded tool-use loop for evidence lookups in the investigators
- retry with the validation error fed back
- easy to stub in tests, since no test may make a live call

The requirement is **not** an autonomous multi-step agent that plans its own workflow.
The whole architecture is a deliberate argument against that.
A framework that pushes us toward free-running agent loops is working against the design, not for it.

### Options

**Anthropic SDK directly, plus our own `llm/client.py`.**
Structured outputs are supported natively by the Claude API, so `complete_structured` is roughly fifty lines: call, parse into the Pydantic model, retry with the error on failure, raise after N attempts.
Zero framework risk, zero abstraction to fight, trivially stubbable.
Cost: we write the retry and tool-loop logic ourselves, maybe a hundred lines total.

**Pydantic AI.**
Typed agents with Pydantic models as the output contract, tool registration by decorator, model-agnostic, testable without network calls.
It fits this codebase almost exactly, because our domain layer is already Pydantic and the output contract is already a Pydantic model.
Cost: one more dependency, and its abstractions have to be understood before they help.

**Claude Agent SDK.**
Built for agentic applications around Claude Code: custom MCP tools via a `@tool()` decorator, subagents defined programmatically, hooks that intercept tool use and file operations, fine-grained permissions, extended thinking control, session management, and JSON Schema structured output.
Genuinely powerful, and the hooks and subagent model map onto the `.agents/` idea nicely.
But it is designed around a coding-assistant session model: sessions, permissions, file tools, resumption.
For one constrained decision call per site, most of that surface is unused, and the session abstraction is a poor fit for a request-response API where the pipeline, not the agent, owns control flow.

**LangGraph.**
Explicit graph-structured agent workflows with state and checkpointing.
It is the right tool when the control flow genuinely belongs to the agent framework.
Here the control flow is already explicit, deterministic Python in `orchestration/`, deliberately.
Adopting LangGraph would mean expressing that flow twice, or handing our deterministic pipeline to a framework designed to make flows non-deterministic.

### Recommendation

**Pydantic AI**, or the Anthropic SDK directly if we want zero framework risk.

The tiebreaker: our domain layer is already Pydantic v2 and our output contract is already a Pydantic model, so Pydantic AI adds typed tool calling and retry handling without a translation layer.
If we find ourselves fighting it in the first hour, fall back to the plain SDK, because `llm/client.py` is small enough that writing it by hand is a real option rather than a defeat.

The Claude Agent SDK is the better choice for a different product: an assistant that explores the codebase or the data on its own.
That is not what the Coordinator is.

**To decide:** whether the hackathon rewards or requires using a specific SDK.
If it does, that changes the answer, and the honest framing is that we are using it for the investigators' tool loop rather than pretending the whole pipeline is agentic.

---

## ADR-006: Next.js, React, TypeScript for the dashboard

**Status:** Accepted. Supersedes the original Vite decision.

The dashboard is a live operations view with several independent panels and a re-planning loop that changes state underneath the user.
That is component-state work, which React handles well and a server-rendered template does not.

Next.js App Router rather than Vite, for three concrete reasons:

1. **Deployment is a `git push`.** Vercel is the deploy target, and a Next.js app needs no build configuration, no static host to pick, and no CI deploy step we have to maintain during a hackathon.
2. **The API proxy is production configuration, not a dev-only convenience.** Vite's proxy exists only in the dev server, so a Vite build would have needed CORS on the backend plus a separate production base URL. Next.js `rewrites()` in `next.config.ts` applies in development and in production alike, so `/api/*` is same-origin everywhere and there is one place to point at the backend.
3. **Server components keep the fetching boundary honest.** Panels that just render a fetched plan can be server components. Only the pieces that genuinely need state, such as the capacity controls and the live re-plan indicator, become client components.

TypeScript strict, with API types generated from the backend OpenAPI schema rather than hand-written.

Considered: Vite (what we started with, simpler build, but every advantage above would have had to be rebuilt by hand), Streamlit (fastest to a demo, all Python, but we lose the pixel-level control the UI standard in `AGENTS.md` demands, and the dashboard is a core deliverable rather than a viewer).

Cost of this choice, stated honestly: Next.js is a heavier framework than this dashboard strictly needs, and the server-versus-client component split is a real thing to learn if you have not used the App Router.
The default is server components; add `'use client'` only where state, effects, or event handlers require it.

`next lint` is deprecated as of Next.js 16, so the `lint` script calls the ESLint CLI directly with a flat config that extends `next/core-web-vitals` and `next/typescript`.

---

## ADR-007: assistant-ui for the dashboard

**Status:** Rejected for the main surface. Possible as a small side panel.

assistant-ui is an open-source React library of primitives for AI chat interfaces: ChatGPT-style components, streaming, multi-turn conversation management, retry and interruption handling.
It is good at what it does.

What it does is chat.
`CLAUDE.md` says explicitly that ReefCommand is not a coral chatbot, and the output is meant to read like an operations plan rather than a conversation.
Building the main surface on chat primitives would push the product toward exactly the framing we decided not to have.

Where it could earn its place: a narrow "ask about this plan" side panel, after the closed loop works, strictly as a read-only explainer over an already-computed plan.
That is a P2 at best.
If a feature does not strengthen the closed loop, it is secondary.

---

## ADR-008: Charting library

**Status:** Proposed. Decide before `[frontend] Evidence panel for one site` starts.

The evidence panel has a hard constraint: the four support scores must never be rendered as parts of a whole.
No pie, no stacked bar, no percentages of 100.
So the requirement is modest: grouped or independent horizontal bars, a confidence indicator, and a small time series for DHW.

**Recommendation: no charting library at first.**
Four bars and a sparkline are less code in plain SVG or CSS than the configuration needed to make a chart library render them the way this panel needs, and a library's defaults will fight the constraint above rather than help with it.

If a real charting need appears later, Recharts is the low-friction React option and Visx gives more control at more cost.

---

## ADR-009: uv and npm for dependencies

**Status:** Accepted

`uv` for Python: fast, lockfile-based, handles the Python version itself, and `uv sync --locked` in CI fails loudly if the lockfile drifts from `pyproject.toml`.
`npm` for the frontend: `package-lock.json` is committed and CI uses `npm ci`.

Both lockfiles are committed, so CI and every laptop resolve identically.

---

## ADR-010: Where the LLM is allowed to run

**Status:** Accepted

Restating it here because it is a technology decision as much as an architectural one, and it constrains every framework choice above.

LLM-backed: the disease, runoff, and physical investigators, and the Coordinator.
Everything else is deterministic: ingestion, thermal evidence, fusion, the policy engine, the optimizer, orchestration, and the API.

Any proposal to add an LLM call outside those four places needs to argue why a documented rule cannot do the job.

---

## ADR-011: Deployment split

**Status:** Proposed. Decide before the demo, not before the code.

Choosing Vercel for the dashboard splits the deployment, because Vercel does not host a long-running Python process the way the pipeline wants.

- **Dashboard:** Vercel. Connect the repository, and `main` deploys itself. Set `REEFCOMMAND_API_URL` as an environment variable so the rewrite points at the deployed backend.
- **Backend:** somewhere that runs a persistent Python process. Railway, Render, or Fly all take a Dockerfile or a start command and are free or near-free at this scale.

Alternative worth knowing about: Vercel can run Python serverless functions, so the backend could live in the same project.
It is not recommended here.
The pipeline holds in-memory plan state across requests, and the OR-Tools solve plus several LLM calls sits uncomfortably against serverless cold starts and execution limits.

The honest fallback: **run everything locally for the demo.**
`docs/demo-runbook.md` already assumes a cached, offline-capable run, and a laptop with no network dependency is the most reliable three minutes we can buy.
Deploying is for sharing the project afterwards, not for the demo itself.
That is why this ADR is proposed rather than accepted: it does not block any issue in the backlog.

---

## Open questions

- ADR-005: which agent framework, and does the hackathon constrain it
- ADR-008: confirm no charting library, or pick one
- ADR-011: where the Python backend is deployed, if we deploy at all
- Persistence: in-memory state is fine for the demo. If we want the plan history to survive a restart, SQLite is the obvious answer and nothing else in the design changes.