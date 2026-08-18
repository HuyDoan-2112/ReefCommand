"""Tests for the grounded disease agent without a live model call."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

import reefcommand
from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.provenance import FixtureSet
from reefcommand.domain.site import ReefSite
from reefcommand.evidence.disease import DiseaseAssessment, DiseaseAgent
from reefcommand.ingestion.field_reports import load_demo_updates, structure
from reefcommand.tools.agrra import AgrraSctldTool
from reefcommand.tools.contracts import EvidenceSnapshot, EvidenceWindow


class FakeDiseaseCompleter:
    def __init__(self) -> None:
        self.system_prompts: list[str] = []
        self.user_prompts: list[str] = []

    def __call__(
        self,
        system: str,
        user: str,
        schema: type[DiseaseAssessment],
    ) -> DiseaseAssessment:
        self.system_prompts.append(system)
        self.user_prompts.append(user)
        return schema(
            support=0.72,
            confidence=0.61,
            rationale="The lesion description and nearby records provide disease support.",
        )


def _site(site_id: str) -> ReefSite:
    path = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"
    fixture = FixtureSet[ReefSite].model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return next(record.data for record in fixture.records if record.data.site_id == site_id)


def _snapshot(site_id: str) -> EvidenceSnapshot:
    as_of = datetime(2023, 9, 15, 12, tzinfo=UTC)
    window = EvidenceWindow(as_of=as_of, start=as_of - timedelta(days=60), end=as_of)
    result = AgrraSctldTool().read(site_id, window)
    return EvidenceSnapshot(
        snapshot_id=f"disease-test-{site_id}",
        site_id=site_id,
        as_of=as_of,
        captured_at=as_of + timedelta(minutes=1),
        results=[result],
    )


def test_agent_returns_model_score_and_agent_owned_citations() -> None:
    site = _site("cheeca_rocks")
    observation = structure(load_demo_updates()[0])
    completer = FakeDiseaseCompleter()

    evidence = DiseaseAgent(completer).assess(site, [observation], _snapshot(site.site_id))

    assert evidence.cause is Cause.DISEASE
    assert evidence.support == 0.72
    assert evidence.confidence == 0.61
    assert len(evidence.citations) >= 2
    assert all(citation.provenance is Provenance.SYNTHETIC for citation in evidence.citations)
    assert "synthetic repository fixture" in evidence.rationale
    assert "AGRRA" in completer.user_prompts[0]
    assert "Do not diagnose SCTLD" in completer.system_prompts[0]


def test_agent_rejects_snapshot_for_another_site() -> None:
    site = _site("cheeca_rocks")
    observation = StructuredObservation(
        report_id="test-report",
        site_id=site.site_id,
        observed_at=datetime(2023, 9, 15, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="site_id"):
        DiseaseAgent(FakeDiseaseCompleter()).assess(
            site,
            [observation],
            _snapshot("sombrero"),
        )
