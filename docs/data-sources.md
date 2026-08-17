# Data sources

Every adapter records, for every value it returns, whether the value came from a live call or from cache, and the timestamp of the snapshot.

## NOAA Coral Reef Watch

Products used: Degree Heating Weeks, Coral Bleaching HotSpot, Bleaching Alert Area, sea-surface temperature, bleaching outlook.
Alert-level definitions come from the 5km product methodology at `coralreefwatch.noaa.gov/product/5km/`.

Rule: pre-fetch and cache the study area and replay window before any demo.
Never depend on a live NOAA call during a live presentation.
Any live call used for effect is wrapped with a short timeout, default 3 seconds, with automatic fallback to the cached copy.

## AGRRA Caribbean Coral Health Watch / SCTLD Tracking Map

Source: `agrra.org/coral-disease-outbreak`.
Used by the disease investigator to find reviewed disease and bleaching reports near a site.

Preserve each returned record's source metadata: submission date, review status, reporting organization.
Do not discard it after the lookup.

Geographic proximity to a reviewed record is supporting evidence, not confirmation.
Proximity alone is never treated as proof that a new field report is SCTLD.
It feeds the disease support score alongside the lesion description, not as a binary override.

Do not assert that all Florida records in this map are sourced specifically from FWC's Fish and Wildlife Research Institute.
Describe the map as AGRRA's reviewed regional tracker.
NOAA references the AGRRA map in its own SCTLD implementation planning.

Do not assume the dashboard allows unrestricted automated scraping.
Cache a snapshot for the demo sites ahead of time through a permitted export or a manually curated snapshot, or request access.

## Rainfall, turbidity, storm tracks, vessel activity

Used by the runoff and physical-damage investigators.
If a real source is not wired up, the module falls back to a clearly labeled synthetic signal.
Synthetic means synthetic on the dashboard, in the API response, and in the logs.

## Reef sites

Study area: the seven Florida Keys sites associated with NOAA Mission: Iconic Reefs.

Do not claim NOAA ranks these sites from most to least ecologically valuable.
NOAA confirms the seven sites are ecologically and culturally significant.
It does not numerically rank them.

## CREMP correspondence

FWC's Coral Reef Evaluation and Monitoring Project provides coral cover, condition, abundance, and diversity data, including downloadable site-level data, and supports percent-cover and diversity calculations.

CREMP monitors roughly 40 sites across the Florida Keys.
Mission: Iconic Reefs covers seven specific restoration sites.
These are not a 1:1 mapping.

Use CREMP measurements only where a given Iconic Reefs site has suitable spatial and habitat correspondence to a CREMP station.
When a match is used, record the distance, the habitat type, and the matching method in the site record.
Where no suitable coverage exists, use another cited monitoring source or a clearly labeled synthetic placeholder.
Never substitute silently.

## Operational resources

We do not have access to a live organization fleet or personnel system.
Boats, dive teams, inventory, budget, and daylight hours are clearly labeled simulated management scenarios in `backend/src/reefcommand/data/scenarios/`.

Do not pretend simulated resource data are real.
The adapter boundary is designed so these inputs can later be replaced by an organization's actual operational systems without touching the pipeline.
