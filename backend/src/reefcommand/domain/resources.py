"""Operational capacity models.

We do not have access to a live organization fleet or personnel system.
Everything in this module is a clearly labeled simulated management scenario.

Do not pretend simulated resource data are real.
The `provenance` field is required, not optional, so a scenario cannot be loaded
without declaring what it is.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    available_hours: float = Field(
        ge=0.0,
        description=(
            "Team-level elapsed in-water hours available in the planning window. "
            "These are not diver-hours and must not be multiplied by diver_count."
        ),
    )
    available_hours_basis: Literal["team_elapsed_hours"] = Field(
        default="team_elapsed_hours",
        description="The unit represented by available_hours.",
    )
    certifications: list[str] = Field(default_factory=list)


class EquipmentItem(BaseModel):
    """A named piece of simulated equipment held in the inventory."""

    model_config = ConfigDict(frozen=True)

    equipment_id: str
    name: str
    category: Literal["shade", "monitoring", "sampling"]
    available_units: int = Field(ge=0)
    unit_label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class Inventory(BaseModel):
    model_config = ConfigDict(frozen=True)

    shade_units: int = Field(default=0, ge=0)
    monitoring_kits: int = Field(default=0, ge=0)
    sampling_kits: int = Field(default=0, ge=0)
    equipment: list[EquipmentItem] = Field(
        default_factory=list,
        description="Named equipment details backing the category totals above.",
    )

    @model_validator(mode="after")
    def equipment_totals_match_categories(self) -> Inventory:
        """Prevent named equipment details from drifting from solver totals."""
        if not self.equipment:
            return self
        actual = {"shade": 0, "monitoring": 0, "sampling": 0}
        for item in self.equipment:
            actual[item.category] += item.available_units
        expected = {
            "shade": self.shade_units,
            "monitoring": self.monitoring_kits,
            "sampling": self.sampling_kits,
        }
        if actual != expected:
            raise ValueError(
                "named equipment totals must match shade_units, monitoring_kits and sampling_kits"
            )
        return self


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

    @model_validator(mode="after")
    def require_simulated_provenance(self) -> ResourceScenario:
        """Reject resource data that could be displayed as live capacity."""
        if self.provenance is not Provenance.SIMULATED:
            raise ValueError("prototype resource scenarios must use simulated provenance")
        return self

    @property
    def is_simulated(self) -> bool:
        return self.provenance is Provenance.SIMULATED

    def display_banner(self) -> str:
        """Text the dashboard shows above any plan built from this scenario."""
        if self.is_simulated:
            return (
                "Simulated operational capacity. Not a real organization's fleet or personnel data."
            )
        raise ValueError("cannot display a resource scenario without simulated provenance")
