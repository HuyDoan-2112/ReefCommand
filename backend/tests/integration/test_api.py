"""HTTP-level checks for the backend entry points."""

from __future__ import annotations

import json

import httpx
import pytest

from reefcommand.api import state as api_state
from reefcommand.api.app import create_app
from reefcommand.config import get_settings
from reefcommand.ingestion.field_reports import load_demo_updates

SITE_IDS = [
    "carysfort",
    "horseshoe",
    "cheeca_rocks",
    "sombrero",
    "newfound_harbor",
    "looe_key",
    "eastern_dry_rocks",
]


@pytest.mark.asyncio
async def test_live_recompute_requires_configured_provider_credential(monkeypatch) -> None:
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()

    def fail_recompute(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("pipeline ran without a live provider credential")

    monkeypatch.setattr(api_state, "recompute", fail_recompute)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plan/recompute",
            json={"execution_mode": "live_llm", "site_ids": ["cheeca_rocks"]},
        )

    assert response.status_code == 409
    assert "REEFCOMMAND_DEEPSEEK_API_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_live_recompute_forces_provider_execution(monkeypatch) -> None:
    monkeypatch.setenv("REEFCOMMAND_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("REEFCOMMAND_DEEPSEEK_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(api_state, "_current_plan", None)
    baseline = api_state.current_plan()
    received: dict[str, object] = {}

    def capture_recompute(
        scenario_id: str,
        site_ids: list[str],
        *,
        offline: bool | None = None,
        demo_data: bool | None = None,
    ) -> object:
        received.update(
            scenario_id=scenario_id,
            site_ids=site_ids,
            offline=offline,
            demo_data=demo_data,
        )
        return baseline

    monkeypatch.setattr(api_state, "recompute", capture_recompute)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/plan/recompute",
            json={
                "scenario_id": "demo_default",
                "site_ids": ["cheeca_rocks"],
                "execution_mode": "live_llm",
            },
        )

    assert response.status_code == 200
    assert received == {
        "scenario_id": "demo_default",
        "site_ids": ["cheeca_rocks"],
        "offline": False,
        "demo_data": True,
    }


@pytest.mark.asyncio
async def test_health_and_sites_do_not_trigger_pipeline_execution(monkeypatch) -> None:
    monkeypatch.setattr(api_state, "_current_plan", None)

    def fail_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("read-only endpoint triggered the planning pipeline")

    monkeypatch.setattr(api_state, "run", fail_run)
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health/data-sources")
        sites = await client.get("/sites")

    assert health.status_code == 200
    assert health.json()["status"] == "no_plan"
    assert sites.status_code == 200
    assert sites.json() == []


@pytest.mark.asyncio
async def test_api_exposes_plan_evidence_provenance_and_replanning() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        recompute = await client.post(
            "/plan/recompute",
            json={"scenario_id": "demo_default", "site_ids": SITE_IDS},
        )
        assert recompute.status_code == 200
        assert recompute.json()["scenario_banner"].startswith("Simulated operational capacity")
        plan_id = recompute.json()["plan_id"]

        trace = await client.get(f"/plan/{plan_id}/trace")
        assert trace.status_code == 200
        trace_payload = trace.json()
        assert len(trace_payload["steps"]) == len(SITE_IDS) * 8 + 1
        assert [step["sequence"] for step in trace_payload["steps"]] == list(
            range(1, len(trace_payload["steps"]) + 1)
        )
        assert trace_payload["steps"][-1]["stage"] == "optimizer"
        serialized_trace = json.dumps(trace_payload).lower()
        assert "api_key" not in serialized_trace
        assert "authorization" not in serialized_trace

        site_trace = await client.get(f"/plan/{plan_id}/trace/cheeca_rocks")
        assert site_trace.status_code == 200
        site_steps = site_trace.json()["steps"]
        assert [step["stage"] for step in site_steps] == [
            "evidence_tools",
            "thermal_investigator",
            "disease_investigator",
            "runoff_investigator",
            "physical_investigator",
            "evidence_fusion",
            "policy_eligibility",
            "coordinator",
            "optimizer",
        ]
        coordinator = next(step for step in site_steps if step["stage"] == "coordinator")
        assert coordinator["output"]["decision"]["reasoning_summary"]
        assert coordinator["validation_checks"] == [
            "pydantic_schema",
            "coordinator_business_rules",
        ]

        sites = await client.get("/sites")
        assert sites.status_code == 200
        assert len(sites.json()) == len(SITE_IDS)

        evidence = await client.get("/sites/cheeca_rocks/evidence")
        assert evidence.status_code == 200
        assert set(evidence.json()["by_cause"]) == {"thermal", "disease", "runoff", "physical"}

        sources = await client.get("/health/data-sources")
        assert sources.status_code == 200
        assert sources.json()["sources"]
        assert all(source["status"] == "synthetic_fixture" for source in sources.json()["sources"])

        update = load_demo_updates()[0]
        observation = await client.post(
            "/observations",
            json=update.model_dump(mode="json"),
        )
        assert observation.status_code == 200
        assert observation.json()["plan"]["replan_trigger"].startswith("new_evidence:")
        observation_plan_id = observation.json()["plan"]["plan_id"]

        resource = await client.patch(
            "/resources/scenario",
            json={
                "scenario_id": "demo_boat_b_unavailable",
                "description": "Boat B out of service",
            },
        )
        assert resource.status_code == 200
        assert resource.json()["plan"]["scenario_id"] == "demo_boat_b_unavailable"

        resource_plan_id = resource.json()["plan"]["plan_id"]
        resource_trace = await client.get(f"/plan/{resource_plan_id}/trace")
        assert resource_trace.status_code == 200
        assert resource_trace.json()["parent_plan_id"] == observation_plan_id
        assert [step["stage"] for step in resource_trace.json()["steps"]] == ["optimizer"]
        assert resource_trace.json()["steps"][0]["inputs"]["reused_evidence"] is True
