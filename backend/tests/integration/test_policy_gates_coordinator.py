"""The Coordinator cannot approve an action the policy engine did not offer.

This is the load-bearing rule of the architecture: the LLM does not invent
interventions.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Policy engine and validation not implemented yet.")


def test_unknown_action_id_is_rejected() -> None:
    raise NotImplementedError


def test_action_with_unmet_evidence_requirements_is_rejected() -> None:
    raise NotImplementedError


def test_contraindicated_action_is_rejected() -> None:
    raise NotImplementedError
