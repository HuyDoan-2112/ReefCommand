# Track: frontend

Label: `track:frontend`

## You own

`frontend/` in its entirety.

## You do not own

Anything under `backend/`.
If you need an endpoint changed or a field added, open an issue against the track that owns it rather than editing it yourself.

## The stack

Next.js App Router, React, TypeScript, deployed to Vercel.
See `docs/tech-decisions.md` ADR-006.

Default to server components.
Add `'use client'` only where you need state, effects, or event handlers, which in practice means the capacity controls and the live re-plan indicator.

`src/app/` is routing and composition only.
A page assembles features; it does not implement them.

`/api/*` is rewritten to the Python backend by `next.config.ts`, in development and in production alike, so everything is same-origin and there is no CORS setup and no base URL scattered through feature code.

## What you are building

This is the last implementation track.
Start feature work after the backend serves stable fixture responses matching the OpenAPI contract.

A dashboard that reads like an operations plan, not like an AI answer.

Four surfaces, one feature folder each:

- `features/plan/` - the current response plan: boat, team, site, action, priority, plus why
- `features/evidence/` - four support scores for one site, with confidence and citations
- `features/resources/` - the simulated scenario and the controls that change it
- `features/evaluation/` - the evaluation numbers, each reported separately

## Rules that are specifically yours

**Never render the four support scores as parts of a whole.**
No pie chart, no stacked bar, no percentages summing to 100.
They do not sum to 1, and the causes are not independent.
Four independent bars or a grouped layout.

**Label them "support", not "probability" or "likelihood".**

**Always show confidence next to support.**
0.8 at confidence 0.3 is a different situation from 0.8 at confidence 0.9, and the manager has to see that.

**The simulated-data banner is not dismissible.**
The backend ships the banner text on the plan object so it cannot be dropped. Do not drop it.

**Distinguish live, cache, simulated, and synthetic visually**, and legibly for someone who is not colorblind-typical.

**When the Coordinator asked for more evidence, show what it asked for and why.**
That is the product working, not failing, and it should look deliberate.

**Every assignment shows that it requires manager approval.**
The system is decision support and should look like it.

## The UI standard

Be picky. Be obsessed with pixel perfection.
Alignment, spacing, typography, contrast, focus states, loading, empty, error, responsive.
If something looks off, fix it even when it is unrelated to your current task.
Verify at the resolution the demo will actually run at, not just your laptop.

## Unblocking yourself

Once the API serves fixtures, generate types from the OpenAPI schema and build against those.
Do not invent a parallel response shape in the frontend while the backend contract is still changing.
When the real pipeline lands, nothing in your code should need to change.
