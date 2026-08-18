"""HTTP-level checks for the backend entry points."""

from __future__ import annotations

import httpx
import pytest

from reefcommand.api.app import create_app
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
async def test_api_exposes_plan_evidence_provenance_and_replanning() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        recompute = await client.post(
            "/plan/recompute",
            json={"scenario_id": "demo_default", "site_ids": SITE_IDS},
        )
        assert recompute.status_code == 200
        assert recompute.json()["scenario_banner"].startswith("Simulated operational capacity")

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

        resource = await client.patch(
            "/resources/scenario",
            json={
                "scenario_id": "demo_boat_b_unavailable",
                "description": "Boat B out of service",
            },
        )
        assert resource.status_code == 200
        assert resource.json()["plan"]["scenario_id"] == "demo_boat_b_unavailable"
