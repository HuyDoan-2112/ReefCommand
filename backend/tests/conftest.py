"""Shared test fixtures.

No test in this suite makes a live external call by default.
Anything that needs one is marked `external` and is deselected in CI.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from reefcommand.config import get_settings


@pytest.fixture(autouse=True)
def _isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Never inherit developer secrets or hit a live service from ordinary tests."""
    monkeypatch.setenv("REEFCOMMAND_FORCE_CACHE", "true")
    monkeypatch.setenv("REEFCOMMAND_OFFLINE_DEMO", "true")
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("REEFCOMMAND_LLM_MODEL", "test-model")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
