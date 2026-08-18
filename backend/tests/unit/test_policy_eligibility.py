"""Tests for source-backed knowledge retrieval and deterministic eligibility."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import Cause
from reefcommand.domain.evidence import CauseEvidence
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.site import ReefSite
from reefcommand.evidence.fusion import fuse
from reefcommand.policy import engine, knowledge_base


def _site(site_id: str = "cheeca_rocks") -> ReefSite:
    path = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"
    fixture = FixtureSet[ReefSite].model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return next(record.data for record in fixture.records if record.data.site_id == site_id)


def _evidence(cause: Cause, support: float, confidence: float = 0.8) -> CauseEvidence:
    return CauseEvidence(
        cause=cause,
        support=support,
        confidence=confidence,
        rationale=f"fixture {cause.value}",
        computed_at=datetime(2023, 9, 15, tzinfo=UTC),
    )


def _fused(
    *,
    thermal: float = 0.8,
    disease: float = 0.7,
    runoff: float = 0.1,
    physical: float = 0.1,
) -> object:
    return fuse(
        "cheeca_rocks",
        [
            _evidence(Cause.THERMAL, thermal),
            _evidence(Cause.DISEASE, disease),
            _evidence(Cause.RUNOFF, runoff),
            _evidence(Cause.PHYSICAL, physical),
        ],
    )


def test_catalog_loader_and_retrieval_preserve_source_backed_actions() -> None:
    catalog = knowledge_base.load_catalog()
    disease_actions = knowledge_base.retrieve({Cause.DISEASE})

    assert len(catalog) == 6
    assert disease_actions
    assert all(Cause.DISEASE in action.applicable_causes for action in disease_actions)
    assert all("http" in action.provenance for action in disease_actions)
    assert knowledge_base.get("targeted_disease_survey").action_id == "targeted_disease_survey"


def test_policy_returns_action_with_missing_evidence_requirements() -> None:
    site = _site()
    candidates = engine.eligible_actions(site, _fused(), observations=[])
    by_id = {candidate.action_id: candidate for candidate in candidates}

    assert "targeted_disease_survey" in by_id
    assert by_id["targeted_disease_survey"].unmet_evidence_requirements == [
        "A field report describes lesions or tissue loss"
    ]
    assert "intensive_monitoring" in by_id
    assert by_id["intensive_monitoring"].unmet_evidence_requirements == []


def test_policy_marks_observation_specific_requirements_as_met() -> None:
    site = _site()
    observation = StructuredObservation(
        report_id="policy-test",
        site_id=site.site_id,
        observed_at=datetime(2023, 9, 15, tzinfo=UTC),
        tissue_loss_observed=True,
        lesion_description="Distinct tissue-loss margin.",
    )

    candidates = engine.eligible_actions(site, _fused(), [observation])
    by_id = {candidate.action_id: candidate for candidate in candidates}

    assert by_id["targeted_disease_survey"].unmet_evidence_requirements == []
    assert by_id["biosecurity_workflow"].unmet_evidence_requirements == [
        "A dive is already scheduled at this site"
    ]


def test_policy_requires_relevant_support_before_retrieving_an_action() -> None:
    site = _site()
    candidates = engine.eligible_actions(
        site,
        _fused(thermal=0.4, disease=0.1, runoff=0.1, physical=0.1),
        [],
    )

    assert {candidate.action_id for candidate in candidates} == {
        "intensive_monitoring",
    }


def test_contraindication_blocks_shading_on_an_open_site() -> None:
    site = _site().model_copy(update={"has_active_restoration": False})

    assert engine.check_contraindications(site, "temporary_shading")
    assert all(
        candidate.action_id != "temporary_shading"
        for candidate in engine.eligible_actions(site, _fused(), [])
    )


def test_policy_rejects_mismatched_fused_evidence() -> None:
    with pytest.raises(ValueError, match="site_id"):
        engine.eligible_actions(
            _site(),
            fuse(
                "sombrero",
                [
                    _evidence(Cause.THERMAL, 0.8),
                    _evidence(Cause.DISEASE, 0.7),
                    _evidence(Cause.RUNOFF, 0.1),
                    _evidence(Cause.PHYSICAL, 0.1),
                ],
            ),
        )
