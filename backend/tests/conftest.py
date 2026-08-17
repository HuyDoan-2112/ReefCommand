"""Shared test fixtures.

No test in this suite makes a live external call by default.
Anything that needs one is marked `external` and is deselected in CI.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _force_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never hit a live external service from the test suite."""
    monkeypatch.setenv("REEFCOMMAND_FORCE_CACHE", "true")


@pytest.fixture
def demo_site_ids() -> list[str]:
    return [
        "carysfort",
        "horseshoe",
        "cheeca_rocks",
        "sombrero",
        "newfound_harbor",
        "looe_key",
        "eastern_dry_rocks",
    ]
