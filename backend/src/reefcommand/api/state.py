"""Small in-process state holder for the prototype API.

The first milestone is a single-process demo, so this module deliberately keeps
the current plan in memory. A production deployment should replace this store
with a database or durable job state without changing the orchestration APIs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock, RLock

from reefcommand.domain.observation import FieldReport
from reefcommand.domain.plan import ResponsePlan
from reefcommand.orchestration.events import NewEvidence, ResourceChange
from reefcommand.orchestration.pipeline import load_scenario, run
from reefcommand.orchestration.replanner import handle

DEFAULT_SCENARIO_ID = "demo_default"
DEFAULT_SITE_IDS = [
    "carysfort",
    "horseshoe",
    "cheeca_rocks",
    "sombrero",
    "newfound_harbor",
    "looe_key",
    "eastern_dry_rocks",
]

_state_lock = Lock()
_mutation_lock = RLock()
_current_plan: ResponsePlan | None = None


def peek_current_plan() -> ResponsePlan | None:
    """Return the published plan without triggering pipeline execution."""
    with _state_lock:
        return _current_plan


def current_plan() -> ResponsePlan:
    """Return the current plan, creating the deterministic demo plan lazily."""
    global _current_plan
    existing = peek_current_plan()
    if existing is not None:
        return existing
    with _mutation_lock:
        existing = peek_current_plan()
        if existing is not None:
            return existing
        computed = run(DEFAULT_SCENARIO_ID, DEFAULT_SITE_IDS)
        with _state_lock:
            _current_plan = computed
        return computed


def recompute(
    scenario_id: str = DEFAULT_SCENARIO_ID,
    site_ids: list[str] | None = None,
) -> ResponsePlan:
    """Create and publish a fresh plan for the requested study area."""
    global _current_plan
    with _mutation_lock:
        computed = run(scenario_id, site_ids or DEFAULT_SITE_IDS)
        with _state_lock:
            _current_plan = computed
        return computed


def apply_observation(report: FieldReport) -> ResponsePlan:
    """Publish the plan produced by a new field report."""
    global _current_plan
    with _mutation_lock:
        computed = handle(
            NewEvidence(received_at=datetime.now(UTC), report=report),
            current_plan(),
        )
        with _state_lock:
            _current_plan = computed
        return computed


def apply_resource_change(
    scenario_id: str,
    description: str,
) -> ResponsePlan:
    """Publish the optimizer-only plan produced by a resource change."""
    global _current_plan
    with _mutation_lock:
        load_scenario(scenario_id)
        current = current_plan()
        computed = handle(
            ResourceChange(
                received_at=datetime.now(UTC),
                scenario_id=scenario_id,
                description=description,
            ),
            current,
        )
        with _state_lock:
            _current_plan = computed
        return computed
