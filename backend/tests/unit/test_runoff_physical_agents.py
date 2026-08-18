"""Tests for runoff and physical agents with model calls replaced by fixtures."""

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
from reefcommand.evidence.physical import PhysicalAgent, PhysicalAssessment
from reefcommand.evidence.runoff import RunoffAgent, RunoffAssessment
from reefcommand.ingestion.field_reports import load_demo_updates, structure
from reefcommand.tools.contracts import EvidenceSnapshot, EvidenceWindow
from reefcommand.tools.rainfall import RainfallTool
from reefcommand.tools.storm_vessel import StormHistoryTool, VesselActivityTool


class FakeCompleter:
    def __init__(self, assessment: object) -> None:
        self.assessment = assessment
        self.prompts: list[str] = []

    def __call__(self, system: str, user: str, schema: type[object]) -> object:
        self.prompts.append(f"{system}\n{user}")
        return self.assessment


def _site(site_id: str = "cheeca_rocks") -> ReefSite:
    path = Path(reefcommand.__file__).resolve().parent / "data/sites/iconic_reefs.yaml"
    fixture = FixtureSet[ReefSite].model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return next(record.data for record in fixture.records if record.data.site_id == site_id)


def _window() -> EvidenceWindow:
    as_of = datetime(2023, 9, 15, 12, tzinfo=UTC)
    return EvidenceWindow(as_of=as_of, start=as_of - timedelta(days=30), end=as_of)


def _observation() -> StructuredObservation:
    return structure(load_demo_updates()[0])


def test_runoff_agent_uses_rainfall_result_and_labels_fixture() -> None:
    site = _site()
    result = RainfallTool().read(site.site_id, _window())
    snapshot = EvidenceSnapshot(
        snapshot_id="runoff-test",
        site_id=site.site_id,
        as_of=_window().as_of,
        captured_at=_window().as_of + timedelta(minutes=1),
        results=[result],
    )
    completer = FakeCompleter(
        RunoffAssessment(
            support=0.62,
            confidence=0.54,
            rationale="Rainfall and turbidity support runoff.",
        )
    )

    evidence = RunoffAgent(completer).assess(site, [_observation()], snapshot)

    assert evidence.cause is Cause.RUNOFF
    assert evidence.support == 0.62
    assert evidence.citations[-1].provenance is Provenance.SYNTHETIC
    assert "synthetic repository fixture" in evidence.rationale
    assert "Rainfall tool result" in completer.prompts[0]


def test_physical_agent_uses_both_context_tools() -> None:
    site = _site()
    window = _window()
    results = [
        StormHistoryTool().read(site.site_id, window),
        VesselActivityTool().read(site.site_id, window),
    ]
    snapshot = EvidenceSnapshot(
        snapshot_id="physical-test",
        site_id=site.site_id,
        as_of=window.as_of,
        captured_at=window.as_of + timedelta(minutes=1),
        results=results,
    )
    completer = FakeCompleter(
        PhysicalAssessment(
            support=0.31,
            confidence=0.48,
            rationale="Vessel activity is context, but no breakage was reported.",
        )
    )

    evidence = PhysicalAgent(completer).assess(site, [_observation()], snapshot)

    assert evidence.cause is Cause.PHYSICAL
    assert evidence.support == 0.31
    assert len(evidence.citations) >= 2
    assert "Storm tool result" in completer.prompts[0]
    assert "Vessel tool result" in completer.prompts[0]


def test_agents_reject_mismatched_snapshot() -> None:
    site = _site()
    window = _window()
    snapshot = EvidenceSnapshot(
        snapshot_id="wrong-site",
        site_id="sombrero",
        as_of=window.as_of,
        captured_at=window.as_of,
        results=[RainfallTool().read("sombrero", window)],
    )

    with pytest.raises(ValueError, match="snapshot site_id"):
        RunoffAgent(
            FakeCompleter(RunoffAssessment(support=0.0, confidence=0.0, rationale="none"))
        ).assess(
            site,
            [],
            snapshot,
        )
