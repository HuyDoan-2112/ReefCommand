"""Loader and validator for the intervention knowledge base.

The knowledge base is data, not code: see data/interventions/catalog.yaml.
Adding an intervention means adding a catalog entry with a citation, not writing
a branch in Python and not prompting a model differently.

Every action must carry: applicable hypothesis, evidence strength, requirements,
contraindications, resource requirements, expected compatibility, and provenance.
Loading fails if any of those are missing, which is why they are required fields
on InterventionDefinition rather than optional ones.
"""

from __future__ import annotations

from pathlib import Path

from reefcommand.domain.intervention import InterventionDefinition


def load_catalog(path: Path | None = None) -> list[InterventionDefinition]:
    """Load and validate the intervention catalog."""
    raise NotImplementedError


def get(action_id: str) -> InterventionDefinition:
    """Return one definition by id. Raises KeyError when unknown."""
    raise NotImplementedError
