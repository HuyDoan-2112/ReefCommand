# ReefCommand dashboard

Next.js App Router, React, TypeScript.
Deploy target is Vercel.

```bash
npm install
npm run dev
```

Runs at `http://localhost:3000`.
`/api/*` is rewritten to the Python backend by `next.config.ts`, so both run side by side with no CORS setup and no base URL scattered through feature code.
Point `REEFCOMMAND_API_URL` at the backend if it is not on `http://127.0.0.1:8000`.

Checks, all of which CI runs:

```bash
npm run lint
npm run typecheck
npm run format:check
npm run build
```

## Structure

```text
src/
  app/          App Router entry. Layout, providers, routes. Composition only.
  api/          Typed fetch client for the backend.
  types/        Types generated from the backend OpenAPI schema.
  components/   Presentational pieces reused across features.
  features/     One folder per dashboard surface. This is where feature code lives.
  hooks/        Shared data hooks.
```

Feature folders own their own components, hooks, and types.
Something only moves up into `components/` or `hooks/` once a second feature actually needs it.

`src/app/` holds routing and composition, not logic.
A page assembles features; it does not implement them.

## Server and client components

Default to server components.
Add `'use client'` only where you need state, effects, or event handlers.

`app/providers.tsx` is a client component because React Query's cache must not be shared across server requests.
That is why the query client is created inside `useState` rather than at module scope.

## What the dashboard must show

These are requirements, not nice-to-haves.

- What evidence supported each decision.
- What uncertainty remains.
- What resource constraints caused the trade-offs.
- Why an intervention was considered compatible.
- The simulated-data banner over any plan built from a simulated scenario.
- Live versus cached provenance for every external value.
- Both `ecological_value` and `strategic_value`, with the weights labeled as prototype assumptions.
- Per-module evaluation results, reported separately. Never one combined accuracy number.

## Rendering rules that are not negotiable

The four support scores do not sum to 1 and the causes are not independent.
No pie chart, no stacked bar, no percentages of a whole.
Four independent bars, or a grouped layout.

Label them "support", not "probability".
Always show confidence next to support.

## UI standard

Be picky. Check alignment, spacing, typography, contrast, focus states, loading, empty, and error states, and responsive behavior.
If something looks off, get it fixed even when it is unrelated to the current task.
See `AGENTS.md` and `.agents/teammates/frontend.md`.
