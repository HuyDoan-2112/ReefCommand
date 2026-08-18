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

from functools import lru_cache
from pathlib import Path

import yaml

from reefcommand.config import DATA_DIR
from reefcommand.domain.enums import Cause
from reefcommand.domain.intervention import InterventionDefinition

CATALOG_PATH = DATA_DIR / "interventions" / "catalog.yaml"


def _parse_catalog(path: Path) -> list[InterventionDefinition]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("interventions"), list):
        raise ValueError("intervention catalog must contain an interventions list")
    catalog = [InterventionDefinition.model_validate(entry) for entry in document["interventions"]]
    action_ids = [action.action_id for action in catalog]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("intervention action_id values must be unique")
    return catalog


def load_catalog(path: Path | None = None) -> list[InterventionDefinition]:
    """Load and validate the intervention catalog."""
    return _parse_catalog(path or CATALOG_PATH)


@lru_cache(maxsize=1)
def _default_index() -> dict[str, InterventionDefinition]:
    return {action.action_id: action for action in load_catalog()}


def retrieve(causes: set[Cause] | None = None) -> list[InterventionDefinition]:
    """Retrieve source-backed actions relevant to one or more causes.

    The prototype knowledge base is deliberately structured retrieval rather than
    an embedding search. The catalog is small, and exact cause and policy fields
    are safer than semantic similarity when the result controls real candidate
    actions. Each returned record carries its source text for the Coordinator.
    """
    actions = list(_default_index().values())
    if causes is None:
        return actions
    return [action for action in actions if set(action.applicable_causes) & causes]


def get(action_id: str) -> InterventionDefinition:
    """Return one definition by id. Raises KeyError when unknown."""
    try:
        return _default_index()[action_id]
    except KeyError as exc:
        raise KeyError(f"unknown intervention action {action_id!r}") from exc
