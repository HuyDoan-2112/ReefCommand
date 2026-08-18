"""Contract checks for the generated OpenAPI schema.

The dashboard generates its TypeScript types from this schema, so a route that
does not declare a `response_model` is a route the frontend has to guess at.
FastAPI silently emits an opaque object for those, which type generation turns
into `Record<string, unknown>`. These tests fail loudly instead.
"""

from __future__ import annotations

import httpx
import pytest

from reefcommand.api.app import create_app


def _success_schema(operation: dict[str, object]) -> dict[str, object]:
    responses = operation.get("responses", {})
    assert isinstance(responses, dict)
    for status in ("200", "201"):
        entry = responses.get(status)
        if isinstance(entry, dict):
            content = entry.get("content", {})
            assert isinstance(content, dict)
            media = content.get("application/json", {})
            assert isinstance(media, dict)
            schema = media.get("schema", {})
            assert isinstance(schema, dict)
            return schema
    return {}


def _names_a_model(schema: dict[str, object]) -> bool:
    """True when the schema points at a component rather than an opaque object."""
    if "$ref" in schema:
        return True
    items = schema.get("items")
    return isinstance(items, dict) and "$ref" in items


@pytest.mark.asyncio
async def test_every_route_declares_a_response_model() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()),
        base_url="http://contract",
    ) as client:
        spec = (await client.get("/openapi.json")).json()

    untyped = [
        f"{verb.upper()} {path}"
        for path, operations in spec["paths"].items()
        for verb, operation in operations.items()
        if not _names_a_model(_success_schema(operation))
    ]

    assert untyped == [], f"routes without a response_model: {untyped}"


@pytest.mark.asyncio
async def test_domain_models_reach_the_schema_components() -> None:
    """The shapes the dashboard renders must be nameable, not inlined as objects."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()),
        base_url="http://contract",
    ) as client:
        spec = (await client.get("/openapi.json")).json()

    components = spec["components"]["schemas"]
    for required in (
        "ResponsePlan",
        "Assignment",
        "DeferredSite",
        "FusedEvidence",
        "CauseEvidence",
        "EvidenceCitation",
        "SiteView",
        "SiteScores",
        "ResourceScenario",
        "ScenarioView",
        "ObservationAccepted",
        "DataSourcesHealth",
    ):
        assert required in components, f"{required} is missing from components/schemas"
