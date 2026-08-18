"""DATA-04: every catalog action must be loadable, cited, and resource-expressible.

Run from the backend environment:
    uv run pytest tests/unit/test_intervention_catalog.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import ActionClass, Cause
from reefcommand.domain.intervention import InterventionDefinition, ResourceRequirement

CATALOG = Path(reefcommand.__file__).resolve().parent / "data/interventions/catalog.yaml"


@pytest.fixture(scope="module")
def raw() -> list[dict]:
    document = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    return document["interventions"]


@pytest.fixture(scope="module")
def catalog(raw) -> list[InterventionDefinition]:
    return [InterventionDefinition.model_validate(entry) for entry in raw]


def test_every_entry_validates(catalog) -> None:
    assert len(catalog) >= 1
    for action in catalog:
        assert isinstance(action, InterventionDefinition)


def test_action_ids_are_unique(catalog) -> None:
    ids = [action.action_id for action in catalog]
    assert len(ids) == len(set(ids))


def test_no_provenance_is_still_a_placeholder(catalog) -> None:
    """The whole point of DATA-04. A TODO here means the model is citing nothing."""
    for action in catalog:
        assert "TODO" not in action.provenance
        assert action.provenance.strip()


def test_every_provenance_names_a_retrievable_source(catalog) -> None:
    """A citation a reviewer cannot open is not a citation."""
    for action in catalog:
        assert "http" in action.provenance, action.action_id


def test_every_provenance_states_its_document_type(catalog) -> None:
    """Agency guidance, a formal protocol and a blog post carry different weight.

    A reviewer should be able to discount a source without reading it first.
    """
    kinds = ("protocol", "guidance", "peer-reviewed", "report", "news", "blog")
    for action in catalog:
        assert any(kind in action.provenance.lower() for kind in kinds), action.action_id


def test_declared_resources_are_expressible_by_the_model(raw) -> None:
    """A resource the model cannot carry is a constraint the optimizer cannot apply.

    Before sampling_kits was added to ResourceRequirement, the water quality action
    declared a sampling kit that was silently dropped on load.
    """
    known = set(ResourceRequirement.model_fields)
    for entry in raw:
        declared = set(entry.get("resources") or {})
        assert declared <= known, f"{entry['action_id']} declares unknown {declared - known}"


def test_causes_and_classes_come_from_the_shared_enums(catalog) -> None:
    """The model does not extend either list. That is the point of the enums."""
    for action in catalog:
        assert action.action_class in set(ActionClass)
        assert action.applicable_causes
        for cause in action.applicable_causes:
            assert cause in set(Cause)


def test_any_action_needing_dive_hours_also_needs_people(catalog) -> None:
    for action in catalog:
        if action.resources.dive_hours > 0 and action.action_id != "biosecurity_workflow":
            assert action.resources.dive_teams >= 1, action.action_id


def test_shading_carries_contraindications(catalog) -> None:
    """The one action whose evidence is split must never be offered unconditionally."""
    shading = next(a for a in catalog if a.action_id == "temporary_shading")
    assert shading.contraindications
    assert shading.expected_compatibility <= 0.5
    assert "Great Barrier Reef" in (shading.notes or "")


def test_thresholds_are_ordered_sensibly(catalog) -> None:
    """A high-cost intervention should not be eligible at a lower bar than a survey."""
    by_id = {action.action_id: action for action in catalog}
    survey = by_id["intensive_monitoring"]
    for action in catalog:
        if action.resources.cost_usd > survey.resources.cost_usd:
            assert action.minimum_support >= survey.minimum_support, action.action_id
