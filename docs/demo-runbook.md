# Demo runbook

Target: a reliable three-minute end-to-end demonstration.
A reliable three minutes beats a comprehensive integration that might not load.

## Before the event

1. From `backend/`, run `uv run python ../scripts/prefetch_external_data.py --start YYYY-MM-DD --end YYYY-MM-DD`.
   This caches NOAA DHW for the study area and replay window, and the AGRRA snapshot for the demo sites.
2. Set `REEFCOMMAND_FORCE_CACHE=true` in the demo `.env` unless a live call is deliberately part of the show.
3. Run the backend and frontend checks from their respective folders.
   Lint must be clean, tests must be green, and no tests may be skipped.
4. Run the full demo script twice, end to end, on the machine that will present.
5. Confirm the live-vs-cache indicator renders correctly, so the team can honestly answer "is this live right now".

## Script

### 1. The setup, roughly 30 seconds

Show the dashboard with the seven Florida Keys sites.
Point out `ecological_value` and `strategic_value` as two separate numbers, and that the weights are labeled prototype assumptions.
Point out the simulated-resources banner.

### 2. The first plan, roughly 45 seconds

Show the current response plan: which boat and dive team go where, which site is deferred and why.
Open one site's evidence panel.
Show four support scores that do not sum to 1, and the confidence attached to each.

### 3. The ambiguity, roughly 45 seconds

Pick the site where thermal and disease are both well supported.
Show the Coordinator deciding that evidence is insufficient and requesting close-range lesion imagery rather than committing to an intervention.
This is the point of the product: it says "I do not know yet, here is what would settle it".

### 4. The new evidence, roughly 45 seconds

Submit the diver report: localized tissue loss with visible lesions at Cheeca Rocks.
Watch evidence fusion update, the policy engine re-evaluate eligible actions, the Coordinator approve, and the optimizer produce a new allocation.
Call out the responsiveness number on screen.

### 5. The resource shock, roughly 15 seconds

Mark Boat B unavailable.
The plan becomes infeasible and recomputes.
Show which site got deferred and the stated reason.

## What to say, and what not to say

Say: an AI decision-support system that turns environmental monitoring, field observations, scientific intervention guidance, and limited conservation resources into continuously updated reef-response plans.

Do not say: an AI that saves coral reefs, an autonomous coral treatment system, a coral disease diagnosis model, another NOAA dashboard, or five AI agents working together.

The one-line insight: reef managers do not have a lack-of-data problem, they have a decision-under-resource-constraints problem.

## If something fails live

Cached mode is the default, so an external outage should be invisible.
If the dashboard fails, the replay script prints the same plan to the terminal.
Do not debug on stage.
Fall back to the recorded run and keep talking.
