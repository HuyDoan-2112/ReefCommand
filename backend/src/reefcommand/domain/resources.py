"""Operational capacity models.

We do not have access to a live organization fleet or personnel system.
Everything in this module is a clearly labeled simulated management scenario.

Do not pretend simulated resource data are real.
The `provenance` field is required, not optional, so a scenario cannot be loaded
without declaring what it is.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from reefcommand.domain.enums import Provenance


class Boat(BaseModel):
    model_config = ConfigDict(frozen=True)

    boat_id: str
    name: str
    available: bool = True
    operational_hours: float = Field(ge=0.0)


class DiveTeam(BaseModel):
    model_config = ConfigDict(frozen=True)

    team_id: str
    name: str
    diver_count: int = Field(ge=1)
    available_hours: float = Field(ge=0.0)
    certifications: list[str] = Field(default_factory=list)


class Inventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    shade_units: int = Field(default=0, ge=0)
    monitoring_kits: int = Field(default=0, ge=0)
    sampling_kits: int = Field(default=0, ge=0)


class ResourceScenario(BaseModel):
    """The capacity available for one planning window."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    label: str
    provenance: Provenance = Field(
        description="Simulated for every scenario shipped with the prototype."
    )
    boats: list[Boat]
    dive_teams: list[DiveTeam]
    inventory: Inventory
    budget_usd: float = Field(ge=0.0)
    daylight_hours: float = Field(ge=0.0)

    @property
    def is_simulated(self) -> bool:
        return self.provenance is Provenance.SIMULATED

    def display_banner(self) -> str:
        """Text the dashboard shows above any plan built from this scenario."""
        if self.is_simulated:
            return (
                "Simulated operational capacity. Not a real organization's fleet or personnel data."
            )
        return f"Operational capacity: {self.label}"
