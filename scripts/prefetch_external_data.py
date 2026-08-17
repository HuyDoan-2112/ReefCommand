"""Cache external data for the demo window.

Live external APIs are a demo liability, not a feature.
Run this before the event, then set REEFCOMMAND_FORCE_CACHE=true.

    make prefetch

Caches:
  - NOAA Coral Reef Watch products for the study area and replay window
  - AGRRA SCTLD Tracking Map records near the demo sites

For AGRRA, use a permitted export or a manually curated snapshot.
Do not assume the dashboard allows unrestricted automated scraping.
"""

from __future__ import annotations

import argparse
from datetime import date


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--radius-km", type=float, default=25.0)
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
