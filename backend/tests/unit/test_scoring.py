"""Site value scoring.

The point of these tests is the separation: restoration investment must move
strategic_value and must not move ecological_value.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Scoring not implemented yet.")


def test_restoration_investment_does_not_change_ecological_value() -> None:
    """Two sites with identical ecology score identically on ecological_value."""
    raise NotImplementedError


def test_restoration_investment_raises_strategic_value() -> None:
    raise NotImplementedError


def test_weights_disclaimer_travels_with_the_scores() -> None:
    """The dashboard cannot render the numbers without the assumption label."""
    raise NotImplementedError
