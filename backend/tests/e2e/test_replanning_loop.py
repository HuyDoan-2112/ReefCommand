"""The closed loop, driven through the real entry point.

This is the demo, as a test.
If this file passes, the three minutes on stage work.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.skip(reason="Pipeline not implemented yet.")]


def test_initial_plan_is_produced_within_capacity() -> None:
    raise NotImplementedError


def test_new_field_report_changes_the_plan() -> None:
    """Submit the Cheeca Rocks tissue-loss report and expect a different allocation."""
    raise NotImplementedError


def test_boat_becoming_unavailable_triggers_recompute() -> None:
    """The plan becomes infeasible and the system detects it without being asked."""
    raise NotImplementedError


def test_plan_response_carries_the_simulated_data_banner() -> None:
    """Simulated capacity is never presented as real, including through the API."""
    raise NotImplementedError
