# Shared components

Presentational pieces reused across at least two features.
A component lives in its feature folder until a second feature needs it.

These are here because the mandatory rendering rules apply on every surface.

| Component | Why it is shared |
| --- | --- |
| `SimulatedDataBanner` | Simulated capacity must be labeled wherever it is displayed, and the banner is not dismissible. |
| `ProvenanceBadge` | Live, cache, simulated and synthetic must stay distinguishable without relying on colour. |
| `SupportConfidenceBar` | Support and confidence are always rendered together, and never as parts of a whole. |
| `ConditionBadge` | A severity rating must always travel with the basis it was derived from. |
| `Panel`, `StatTile`, `Button` | Layout chrome ported from `reefcommand.html`. |

See `.agents/teammates/frontend.md` for the rules these encode.
