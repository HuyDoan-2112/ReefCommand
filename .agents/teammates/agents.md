# Track: agents plus backend

Label: `track:agents-backend`

## Priority

This track starts after the data foundation is reproducible.
It owns the decision pipeline and the API that the frontend will consume later.

## You own

- `backend/src/reefcommand/evidence/`
- `backend/src/reefcommand/policy/`
- `backend/src/reefcommand/coordinator/`
- `backend/src/reefcommand/optimizer/`
- `backend/src/reefcommand/orchestration/`
- `backend/src/reefcommand/llm/`
- `backend/src/reefcommand/api/`
- Backend tests for those packages.

## You coordinate

- Domain model changes with the data track.
- OpenAPI response changes with the frontend track.
- Coordinator framework selection through ADR-005.

## First deliverables

- Implement the deterministic offline pipeline before live LLM calls.
- Keep support scores independent and labeled as support, not probability.
- Enforce policy eligibility and Coordinator business rules before optimization.
- Make the optimizer expose assignments, deferrals, and binding constraints.
- Make evidence and resource events re-plan through the real API path.
- Remove skipped integration and end-to-end tests as each path becomes real.

## Rules

- The LLM cannot invent actions or assign resources.
- The optimizer receives typed validated objects, never prose.
- A resource-only event must not rerun unchanged investigators.
- A new evidence event must preserve the original report and its provenance.
- Use fixture-backed tests for every live LLM or external-data boundary.

See `docs/implementation-plan.md` for BACK and AGENT task IDs and acceptance criteria.
