"""Response models for the API surface.

Every route declares a `response_model` so the generated OpenAPI schema
describes the real contract rather than an opaque object. The dashboard
generates its TypeScript types from that schema, so an untyped route is a
route the frontend has to guess at.

Routes that return a domain model directly, such as `GET /plan/current`,
declare that model. This module only holds the composite shapes that have no
single domain model behind them, plus the small status payloads.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Cause, Provenance
from reefcommand.domain.plan import Assignment, DeferredSite, ResponsePlan
from reefcommand.domain.resources import ResourceScenario
from reefcommand.domain.site import ReefSite, SiteScores

DataSourceStatusValue = Literal["live", "cache", "synthetic_fixture"]
"""How the last value for one source reached the pipeline."""


class HealthStatus(BaseModel):
    """Liveness payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["ok"]


class DataSourceStatus(BaseModel):
    """Live-versus-cache standing for one external source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    provenance: list[Provenance] = Field(
        description="Every provenance kind seen for this source in the current evidence snapshot."
    )
    status: DataSourceStatusValue
    note: str


class DataSourcesHealth(BaseModel):
    """Per-source provenance standing behind the current plan.

    `status` is `no_plan` before the first plan is published, in which case
    `sources` is empty. This endpoint never starts a planning run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    checked_at: AwareDatetime
    sources: list[DataSourceStatus]
    status: Literal["ok", "no_plan"] = "ok"


class SiteView(ReefSite):
    """One study-area site with its scores and its standing in the current plan.

    This extends `ReefSite` rather than nesting it, because the site's own
    fields are serialized at the top level of the response.
    """

    scores: SiteScores
    dominant_causes: list[Cause] = Field(
        description="Causes currently in play. More than one can be, and none is valid."
    )
    current_assignment: Assignment | None = None
    deferred: DeferredSite | None = None


class ObservationAccepted(BaseModel):
    """Result of submitting one field report, including the plan it produced."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: str
    plan: ResponsePlan
    replan_latency_ms: int | None = Field(
        default=None,
        description="Measured server-side so the dashboard does not include network noise.",
    )


class ScenarioView(BaseModel):
    """The active simulated capacity scenario and its mandatory banner."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario: ResourceScenario
    banner: str = Field(description="Simulated-data banner. Never drop this in the UI.")


class ResourceChangeResult(BaseModel):
    """The plan produced by a capacity change, with the scenario now in force."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan: ResponsePlan
    scenario: ResourceScenario
    banner: str = Field(description="Simulated-data banner. Never drop this in the UI.")
