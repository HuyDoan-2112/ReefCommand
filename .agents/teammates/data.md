# Track: data

Label: `track:data`

## Priority

The data contract and minimal fixtures are the first dependency.
After that, data curation and Agents plus Backend work in parallel.
The backend must be able to run from reproducible, honestly labeled fixtures before live integrations are attempted.

## You own

- `backend/src/reefcommand/data/`
- `backend/src/reefcommand/ingestion/`
- `scripts/`
- Data-source documentation and fixture validation.

## You coordinate

- Changes to shared provenance fields in `backend/src/reefcommand/domain/`.
- Changes to site, scenario, observation, and intervention payloads consumed by Agents plus Backend.

## First deliverables

- Define the fixture and provenance contract before parallel work begins.
- Complete site, resource, intervention, and demo observation fixtures.
- Implement cache read/write and forced-cache behavior.
- Preserve source URL, snapshot timestamp, review metadata, and provenance.
- Provide deterministic fixture data for the initial plan and the Cheeca Rocks evidence update.
- Make the prefetch and seed scripts executable without a task runner.

Real NOAA and AGRRA adapter work is important, but it must not block the fixture-backed backend path.

## Rules

- Never present synthetic, simulated, or cached data as live data.
- Never silently replace a missing source with a placeholder.
- Preserve AGRRA review status and reporting organization metadata.
- Do not add an LLM call to ingestion or data normalization.

See `docs/implementation-plan.md` for DATA task IDs and acceptance criteria.
