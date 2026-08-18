"""Cache external data for the demo window.

Live external APIs are a demo liability, not a feature.
Run this before the event, with network access, then set REEFCOMMAND_FORCE_CACHE=true.

    cd backend
    uv run python ../scripts/prefetch_external_data.py --start YYYY-MM-DD --end YYYY-MM-DD

Caches:
  - NOAA Coral Reef Watch products for the study area and replay window, fetched
    live from ERDDAP and written to the local cache.
  - AGRRA SCTLD Tracking Map records near the demo sites. AGRRA is snapshot-based:
    the shipped snapshot is a curated placeholder, so this step reports its
    coverage rather than fetching over the network.

For AGRRA, use a permitted export or a manually curated snapshot.
Do not assume the dashboard allows unrestricted automated scraping.
"""

from __future__ import annotations

import argparse
from datetime import date

from reefcommand.ingestion import agrra_sctld, noaa_crw

DEMO_SITE_IDS = [
    "carysfort",
    "horseshoe",
    "cheeca_rocks",
    "sombrero",
    "newfound_harbor",
    "looe_key",
    "eastern_dry_rocks",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Cache NOAA and AGRRA data for the demo window.")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--radius-km", type=float, default=25.0)
    args = parser.parse_args()

    noaa_records = noaa_crw.prefetch_study_area(DEMO_SITE_IDS, args.start, args.end)
    agrra_records = agrra_sctld.prefetch_snapshot(DEMO_SITE_IDS, args.radius_km, args.start)

    print(
        f"Cached {noaa_records} NOAA Coral Reef Watch observations "
        f"for {len(DEMO_SITE_IDS)} sites, {args.start} to {args.end}."
    )
    print(
        f"AGRRA snapshot has {agrra_records} synthetic placeholder records "
        f"within {args.radius_km} km of the demo sites. Replace with a permitted export before use."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
