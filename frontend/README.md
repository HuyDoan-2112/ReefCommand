# ReefCommand dashboard

Vite + React + TypeScript.

```bash
npm install
npm run dev
```

## Structure

```text
src/
  api/          Typed fetch client for the backend.
  types/        Types mirroring the backend Pydantic models.
  components/   Presentational pieces reused across features.
  features/     One folder per dashboard surface. This is where feature code lives.
  hooks/        Shared data hooks.
  pages/        Route-level composition only.
  styles/       Tokens and global CSS.
```

Feature folders own their own components, hooks, and types.
Something only moves up into `components/` or `hooks/` once a second feature
actually needs it.

## What the dashboard must show

These are requirements, not nice-to-haves.

- What evidence supported each decision.
- What uncertainty remains.
- What resource constraints caused the trade-offs.
- Why an intervention was considered compatible.
- The simulated-data banner over any plan built from a simulated scenario.
- Live versus cached provenance for every external value.
- Both `ecological_value` and `strategic_value`, with the weights labeled as
  prototype assumptions.
- Per-module evaluation results, reported separately. Never one combined accuracy
  number.

## UI standard

Be picky. Check alignment, spacing, typography, contrast, focus states, loading,
empty, and error states, and responsive behavior.
If something looks off, get it fixed even when it is unrelated to the current
task.
