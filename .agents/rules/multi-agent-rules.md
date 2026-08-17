# Multi-agent rules

ReefCommand is developed by multiple contributors in parallel.
Ownership prevents accidental changes to shared contracts and overlapping work.

## Track ownership

- The frontend track owns `frontend/`.
- Backend pipeline tracks own their assigned package under `backend/src/reefcommand/` and its tests.
- Data work owns external adapters, cache snapshots, seed data, and data-source provenance.
- Shared domain models, API payloads, and repository-wide configuration are coordination points.
- If a change crosses tracks, describe the contract change and coordinate it before implementation.

## Working in parallel

- Inspect the current worktree before editing; existing changes belong to the user unless clearly yours.
- Do not overwrite or reset another contributor's changes.
- Keep commits focused on one track or one coordinated contract change.
- Prefer fixture-backed interfaces so one track can proceed without waiting for another.
- Record assumptions and blockers in the relevant issue or pull request.

## Handoffs

- State what changed, what was verified, and what remains.
- Name any changed API or domain fields explicitly.
- Include the exact command used for verification and its result.
- Do not silently work around a rule; document the conflict and ask for a deliberate change.
