"""HTTP checks for live field-report structuring and reviewed submission."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import httpx
import pytest

from reefcommand.api import state as api_state
from reefcommand.api.app import create_app
from reefcommand.api.routes import observations as observation_routes
from reefcommand.config import get_settings
from reefcommand.domain.enums import Provenance
from reefcommand.domain.observation import FieldReport, StructuredObservation
from reefcommand.ingestion.llm_field_reports import StructuredReportExtraction
from reefcommand.llm.client import LlmCallMetrics


def _report() -> FieldReport:
    return FieldReport(
        report_id="messy-cheeca-api",
        site_id="cheeca_rocks",
        observed_at=datetime(2023, 9, 15, 14, 5, tzinfo=UTC),
        observer="Demo diver",
        text="Sharp tissue-loss line on brain coral; no percentage estimate.",
        provenance=Provenance.SYNTHETIC,
    )


@pytest.mark.asyncio
async def test_live_structure_requires_provider_credential(monkeypatch) -> None:
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/observations/structure",
            json=_report().model_dump(mode="json"),
        )

    assert response.status_code == 409
    assert "REEFCOMMAND_DEEPSEEK_API_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_live_structure_returns_observation_and_call_metadata(monkeypatch) -> None:
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "test-key")
    get_settings.cache_clear()
    report = _report()

    def fake_structure(received: FieldReport) -> StructuredReportExtraction:
        return StructuredReportExtraction(
            observation=StructuredObservation(
                report_id=received.report_id,
                site_id=received.site_id,
                observed_at=received.observed_at,
                tissue_loss_observed=True,
                lesion_description="Sharp tissue-loss line on brain coral.",
            ),
            extraction_confidence=0.96,
        )

    @contextmanager
    def fake_calls() -> Iterator[list[LlmCallMetrics]]:
        yield [
            LlmCallMetrics(
                provider="deepseek",
                model="deepseek-chat",
                attempt_count=1,
                input_tokens=120,
                output_tokens=45,
            )
        ]

    monkeypatch.setattr(observation_routes, "structure_live", fake_structure)
    monkeypatch.setattr(observation_routes, "collect_llm_calls", fake_calls)
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/observations/structure", json=report.model_dump(mode="json"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "deepseek"
    assert payload["model"] == "deepseek-chat"
    assert payload["input_tokens"] == 120
    assert payload["extraction_confidence"] == 0.96
    assert payload["observation"]["tissue_loss_observed"] is True


@pytest.mark.asyncio
async def test_reviewed_submission_rejects_identity_mismatch(monkeypatch) -> None:
    report = _report()
    observation = StructuredObservation(
        report_id="different-report",
        site_id=report.site_id,
        observed_at=report.observed_at,
    )

    def fail_apply(*_args: object, **_kwargs: object) -> object:
        raise ValueError("structured observation identity must match its raw report")

    monkeypatch.setattr(api_state, "apply_structured_observation", fail_apply)
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/observations/structured",
            json={
                "report": report.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
            },
        )

    assert response.status_code == 422
    assert "identity" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reviewed_submission_replans_with_exact_extraction(monkeypatch) -> None:
    report = _report()
    observation = StructuredObservation(
        report_id=report.report_id,
        site_id=report.site_id,
        observed_at=report.observed_at,
        tissue_loss_observed=True,
        lesion_description="Sharp tissue-loss line on brain coral.",
    )
    monkeypatch.setattr(api_state, "_current_plan", None)
    baseline = api_state.current_plan().model_copy(update={"replan_latency_ms": 321})
    received: dict[str, object] = {}

    def capture_apply(
        received_report: FieldReport,
        received_observation: StructuredObservation,
    ) -> object:
        received.update(report=received_report, observation=received_observation)
        return baseline

    monkeypatch.setattr(api_state, "apply_structured_observation", capture_apply)
    transport = httpx.ASGITransport(app=create_app())

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/observations/structured",
            json={
                "report": report.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
            },
        )

    assert response.status_code == 200
    assert response.json()["replan_latency_ms"] == 321
    assert received == {"report": report, "observation": observation}
