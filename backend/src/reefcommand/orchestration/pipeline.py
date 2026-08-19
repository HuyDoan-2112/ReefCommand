"""End-to-end pipeline for one planning window.

    OBSERVE
       |
    STRUCTURE
       |
    INVESTIGATE                       (four independent investigators)
       |
    FUSE EVIDENCE                     (deterministic)
       |
    CONSTRAIN TO POLICY-ELIGIBLE ACTIONS
       |
    REASON ABOUT UNCERTAINTY          (Coordinator: act now, or get more data)
       |
    OPTIMIZE
       |
    ACT / DISPLAY PLAN

The execution path is dynamic. When the Coordinator finds evidence insufficient,
the case loops back for another observation instead of proceeding to the
optimizer. That changing path is the reason an autonomous agent is warranted at
this one point in the system, and nowhere else.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache, partial
from threading import RLock
from typing import cast

import yaml

from reefcommand.config import DATA_DIR, get_settings
from reefcommand.coordinator.agent import CoordinatorCompleter
from reefcommand.coordinator.agent import decide as decide_coordinator
from reefcommand.domain.enums import Provenance
from reefcommand.domain.evidence import FusedEvidence
from reefcommand.domain.intervention import EligibleAction
from reefcommand.domain.observation import StructuredObservation
from reefcommand.domain.plan import ResponsePlan
from reefcommand.domain.provenance import FixtureSet, ProvenanceMetadata
from reefcommand.domain.resources import ResourceScenario
from reefcommand.domain.site import ReefSite
from reefcommand.evidence import disease, physical, runoff, thermal
from reefcommand.evidence.fusion import fuse
from reefcommand.ingestion.agrra_sctld import NearbyRecords
from reefcommand.ingestion.field_reports import load_demo_reports, structure
from reefcommand.ingestion.noaa_crw import CrwObservation
from reefcommand.llm.client import collect_llm_calls
from reefcommand.optimizer.model import AllocationProblem, build_problem
from reefcommand.optimizer.scoring import score_sites
from reefcommand.optimizer.solver import solve
from reefcommand.orchestration.demo import (
    coordinator_completer as offline_coordinator_completer,
)
from reefcommand.orchestration.demo import (
    disease_completer as offline_disease_completer,
)
from reefcommand.orchestration.demo import (
    physical_completer as offline_physical_completer,
)
from reefcommand.orchestration.demo import (
    runoff_completer as offline_runoff_completer,
)
from reefcommand.orchestration.trace import ExecutionTrace, TraceExecutor, TraceRecorder, TraceStage
from reefcommand.policy.engine import eligible_actions
from reefcommand.tools import (
    AgrraSctldTool,
    EvidenceSnapshot,
    EvidenceWindow,
    RainfallTool,
    StormHistoryTool,
    ToolResult,
    VesselActivityTool,
)

SITES_PATH = DATA_DIR / "sites" / "iconic_reefs.yaml"
SCENARIOS_PATH = DATA_DIR / "scenarios" / "demo_resource_scenarios.yaml"
DEFAULT_LOOKBACK_DAYS = 60


@dataclass(frozen=True)
class PipelineState:
    """Inputs retained for a targeted resource-only replan."""

    plan: ResponsePlan
    problem: AllocationProblem
    site_ids: tuple[str, ...]
    observations: tuple[StructuredObservation, ...]
    evidence_by_site: dict[str, FusedEvidence]
    offline: bool
    trace: ExecutionTrace


MAX_RETAINED_PLAN_STATES = 32
_STATE_BY_PLAN_ID: OrderedDict[str, PipelineState] = OrderedDict()
_STATE_LOCK = RLock()


@lru_cache(maxsize=1)
def _all_sites() -> tuple[ReefSite, ...]:
    fixture = FixtureSet[ReefSite].model_validate(
        yaml.safe_load(SITES_PATH.read_text(encoding="utf-8"))
    )
    return tuple(record.data for record in fixture.records)


@lru_cache(maxsize=1)
def _all_scenarios() -> tuple[ResourceScenario, ...]:
    fixture = FixtureSet[ResourceScenario].model_validate(
        yaml.safe_load(SCENARIOS_PATH.read_text(encoding="utf-8"))
    )
    return tuple(record.data for record in fixture.records)


def load_sites(site_ids: Sequence[str]) -> list[ReefSite]:
    """Load requested sites and fail loudly when a site id is unknown."""
    by_id = {site.site_id: site for site in _all_sites()}
    missing = [site_id for site_id in site_ids if site_id not in by_id]
    if missing:
        raise ValueError(f"unknown site(s): {', '.join(missing)}")
    return [by_id[site_id] for site_id in site_ids]


def load_scenario(scenario_id: str) -> ResourceScenario:
    """Load one simulated resource scenario by id."""
    for scenario in _all_scenarios():
        if scenario.scenario_id == scenario_id:
            return scenario
    raise ValueError(f"unknown resource scenario {scenario_id!r}")


def state_for_plan(plan_id: str) -> PipelineState | None:
    """Return retained pipeline state for a plan, if it was created in-process."""
    with _STATE_LOCK:
        state = _STATE_BY_PLAN_ID.get(plan_id)
        if state is not None:
            _STATE_BY_PLAN_ID.move_to_end(plan_id)
        return state


def remember_state(
    plan: ResponsePlan,
    problem: AllocationProblem,
    site_ids: Sequence[str],
    observations: Sequence[StructuredObservation],
    evidence_by_site: Mapping[str, FusedEvidence],
    offline: bool,
    trace: ExecutionTrace,
) -> None:
    """Retain the typed inputs needed for a later in-process replan."""
    with _STATE_LOCK:
        _STATE_BY_PLAN_ID[plan.plan_id] = PipelineState(
            plan=plan,
            problem=problem,
            site_ids=tuple(site_ids),
            observations=tuple(observations),
            evidence_by_site=dict(evidence_by_site),
            offline=offline,
            trace=trace,
        )
        _STATE_BY_PLAN_ID.move_to_end(plan.plan_id)
        while len(_STATE_BY_PLAN_ID) > MAX_RETAINED_PLAN_STATES:
            _STATE_BY_PLAN_ID.popitem(last=False)


def _synthetic_crw(site_id: str, observed_on: date) -> list[CrwObservation]:
    """Create the labeled NOAA replay input used by the offline demo.

    The values are reconstructed from the cited 2023 heatwave fixtures. They
    are synthetic replay values, not a live NOAA response or a cached snapshot.
    """
    dhw_by_site = {
        "carysfort": 15.2,
        "horseshoe": 12.0,
        "cheeca_rocks": 15.6,
        "sombrero": 14.0,
        "newfound_harbor": 11.9,
        "looe_key": 15.0,
        "eastern_dry_rocks": 10.5,
    }
    dhw = dhw_by_site.get(site_id, 0.0)
    hotspot = 1.0 if dhw > 0 else 0.0
    return [
        CrwObservation(
            site_id=site_id,
            observed_on=observed_on,
            sst_c=30.0,
            hotspot_c=hotspot,
            degree_heating_weeks=dhw,
            alert_level=thermal.alert_level_from_dhw(dhw, hotspot),
            provenance=Provenance.SYNTHETIC,
            provenance_metadata=ProvenanceMetadata(
                kind=Provenance.SYNTHETIC,
                source="ReefCommand 2023 NOAA CRW replay fixture",
                source_url="https://coralreefwatch.noaa.gov/product/5km/",
                observed_at=observed_on,
                note=(
                    "SYNTHETIC. Reconstructed replay value from the cited 2023 heatwave "
                    "fixtures; replace with a permitted NOAA CRW snapshot before live use."
                ),
            ),
        )
    ]


def _window(observations: Sequence[StructuredObservation]) -> EvidenceWindow:
    observed_dates = [observation.observed_at for observation in observations]
    as_of = max(observed_dates, default=datetime(2023, 9, 15, tzinfo=UTC))
    return EvidenceWindow(
        as_of=as_of,
        start=as_of - timedelta(days=DEFAULT_LOOKBACK_DAYS - 1),
        end=as_of,
    )


def _snapshot(site_id: str, window: EvidenceWindow) -> EvidenceSnapshot:
    results: list[ToolResult[object]] = [
        cast(ToolResult[object], AgrraSctldTool().read(site_id, window)),
        cast(ToolResult[object], RainfallTool().read(site_id, window)),
        cast(ToolResult[object], StormHistoryTool().read(site_id, window)),
        cast(ToolResult[object], VesselActivityTool().read(site_id, window)),
    ]
    return EvidenceSnapshot(
        snapshot_id=f"{site_id}:{window.as_of.isoformat()}",
        site_id=site_id,
        as_of=window.as_of,
        captured_at=datetime.now(UTC),
        results=results,
    )


def _assess_site(
    site: ReefSite,
    observations: Sequence[StructuredObservation],
    window: EvidenceWindow,
    *,
    offline: bool,
    demo_data: bool,
    trace: TraceRecorder,
) -> tuple[FusedEvidence, list[EligibleAction]]:
    site_observations = [
        observation for observation in observations if observation.site_id == site.site_id
    ]
    observation_refs = [observation.report_id for observation in site_observations]
    snapshot = trace.record(
        TraceStage.EVIDENCE_TOOLS,
        TraceExecutor.DETERMINISTIC,
        lambda: _snapshot(site.site_id, window),
        site_id=site.site_id,
        inputs={
            "site_id": site.site_id,
            "window": window.model_dump(mode="json"),
        },
        serialize=lambda result: {"snapshot": result.model_dump(mode="json")},
        rationale=lambda result: (
            "Collected one immutable, time-aligned evidence snapshot from "
            f"{len(result.results)} tools."
        ),
        validation_checks=("pydantic_schema", "site_and_time_alignment"),
    )
    crw = _synthetic_crw(site.site_id, window.as_of.date()) if demo_data else None
    thermal_evidence = trace.record(
        TraceStage.THERMAL_INVESTIGATOR,
        TraceExecutor.DETERMINISTIC,
        lambda: thermal.assess(site, list(site_observations), crw_series=crw),
        site_id=site.site_id,
        inputs={
            "site_ref": site.site_id,
            "observation_refs": observation_refs,
            "thermal_source_mode": "synthetic_replay" if demo_data else "noaa_live_or_cache",
        },
        serialize=lambda result: {"evidence": result.model_dump(mode="json")},
        rationale=lambda result: result.rationale,
        validation_checks=("documented_dhw_thresholds", "pydantic_schema"),
    )
    nearby = NearbyRecords.model_validate(snapshot.result("agrra_sctld").data)
    executor = TraceExecutor.FIXTURE if offline else TraceExecutor.LLM
    settings = get_settings()
    provider = None if offline else settings.llm_provider
    model = None if offline else settings.llm_model

    with collect_llm_calls() as disease_calls:
        disease_evidence = trace.record(
            TraceStage.DISEASE_INVESTIGATOR,
            executor,
            lambda: disease.assess(
                site,
                list(observations),
                snapshot,
                completer=(
                    offline_disease_completer(site_observations, nearby) if offline else None
                ),
            ),
            site_id=site.site_id,
            provider=provider,
            model=model,
            inputs={
                "site_ref": site.site_id,
                "observation_refs": observation_refs,
                "tool_result_ref": f"{snapshot.snapshot_id}:agrra_sctld",
            },
            serialize=lambda result: {"evidence": result.model_dump(mode="json")},
            rationale=lambda result: result.rationale,
            validation_checks=("pydantic_schema", "citations_assembled_from_inputs"),
            llm_calls=disease_calls,
        )

    with collect_llm_calls() as runoff_calls:
        runoff_evidence = trace.record(
            TraceStage.RUNOFF_INVESTIGATOR,
            executor,
            lambda: runoff.assess(
                site,
                list(observations),
                snapshot,
                completer=(
                    offline_runoff_completer(site_observations, snapshot) if offline else None
                ),
            ),
            site_id=site.site_id,
            provider=provider,
            model=model,
            inputs={
                "site_ref": site.site_id,
                "observation_refs": observation_refs,
                "tool_result_ref": f"{snapshot.snapshot_id}:rainfall",
            },
            serialize=lambda result: {"evidence": result.model_dump(mode="json")},
            rationale=lambda result: result.rationale,
            validation_checks=("pydantic_schema", "citations_assembled_from_inputs"),
            llm_calls=runoff_calls,
        )

    with collect_llm_calls() as physical_calls:
        physical_evidence = trace.record(
            TraceStage.PHYSICAL_INVESTIGATOR,
            executor,
            lambda: physical.assess(
                site,
                list(observations),
                snapshot,
                completer=(
                    offline_physical_completer(site_observations, snapshot) if offline else None
                ),
            ),
            site_id=site.site_id,
            provider=provider,
            model=model,
            inputs={
                "site_ref": site.site_id,
                "observation_refs": observation_refs,
                "storm_tool_result_ref": f"{snapshot.snapshot_id}:storm_history",
                "vessel_tool_result_ref": f"{snapshot.snapshot_id}:vessel_activity",
            },
            serialize=lambda result: {"evidence": result.model_dump(mode="json")},
            rationale=lambda result: result.rationale,
            validation_checks=(
                "pydantic_schema",
                "citations_assembled_from_inputs",
                "physical_signal_guardrail",
            ),
            llm_calls=physical_calls,
        )

    investigator_outputs = [
        thermal_evidence,
        disease_evidence,
        runoff_evidence,
        physical_evidence,
    ]
    evidence = trace.record(
        TraceStage.EVIDENCE_FUSION,
        TraceExecutor.DETERMINISTIC,
        lambda: fuse(site.site_id, investigator_outputs),
        site_id=site.site_id,
        inputs={"investigator_output_refs": [item.cause.value for item in investigator_outputs]},
        serialize=lambda result: {"fused_evidence": result.model_dump(mode="json")},
        rationale=lambda result: (
            "Deterministically retained independent support scores and identified "
            f"{len(result.dominant_causes)} dominant cause(s)."
        ),
        validation_checks=("one_output_per_cause", "support_scores_not_normalized"),
    )
    candidates = trace.record(
        TraceStage.POLICY_ELIGIBILITY,
        TraceExecutor.DETERMINISTIC,
        lambda: eligible_actions(site, evidence, list(observations)),
        site_id=site.site_id,
        inputs={
            "fused_evidence_ref": f"{site.site_id}:evidence_fusion",
            "observation_refs": observation_refs,
        },
        serialize=lambda result: {
            "eligible_actions": [item.model_dump(mode="json") for item in result]
        },
        rationale=lambda result: (
            f"The policy engine returned {len(result)} source-backed candidate action(s)."
        ),
        validation_checks=("knowledge_base_retrieval", "requirements_and_contraindications"),
    )
    return evidence, candidates


def run(
    scenario_id: str,
    site_ids: list[str],
    *,
    observations: Sequence[StructuredObservation] | None = None,
    replan_trigger: str | None = None,
    offline: bool | None = None,
    demo_data: bool | None = None,
) -> ResponsePlan:
    """Run the full pipeline and return a response plan.

    The default is the explicitly labeled offline demo mode.
    Set ``offline=False`` to use the live structured LLM completers while keeping
    the same tool, fusion, policy, and validation boundaries.
    Set ``demo_data=True`` independently when a live model should reason over the
    labeled, presentation-safe evidence fixtures instead of requiring a live NOAA call.
    """
    sites = load_sites(site_ids)
    scenario = load_scenario(scenario_id)
    if observations is None:
        reports = load_demo_reports(site_ids)
        structured = [structure(report) for report in reports]
    else:
        structured = list(observations)
    if any(observation.site_id not in set(site_ids) for observation in structured):
        raise ValueError("all observations must belong to a requested site")
    window = _window(structured)
    offline_mode = get_settings().offline_demo if offline is None else offline
    demo_data_mode = offline_mode if demo_data is None else demo_data
    trace_recorder = TraceRecorder(
        scenario_id,
        offline=offline_mode,
        trigger=replan_trigger,
    )
    settings = get_settings()
    agent_executor = TraceExecutor.FIXTURE if offline_mode else TraceExecutor.LLM
    agent_provider = None if offline_mode else settings.llm_provider
    agent_model = None if offline_mode else settings.llm_model

    def assess_and_decide(site: ReefSite) -> tuple[str, FusedEvidence, list[EligibleAction]]:
        evidence, candidates = _assess_site(
            site,
            structured,
            window,
            offline=offline_mode,
            demo_data=demo_data_mode,
            trace=trace_recorder,
        )
        coordinator_completer: CoordinatorCompleter | None = (
            offline_coordinator_completer(evidence, candidates) if offline_mode else None
        )
        with collect_llm_calls() as coordinator_calls:
            decision = trace_recorder.record(
                TraceStage.COORDINATOR,
                agent_executor,
                partial(
                    decide_coordinator,
                    evidence,
                    candidates,
                    completer=coordinator_completer,
                ),
                site_id=site.site_id,
                provider=agent_provider,
                model=agent_model,
                inputs={
                    "fused_evidence_ref": f"{site.site_id}:evidence_fusion",
                    "eligible_action_refs": [
                        f"{candidate.site_id}:{candidate.action_id}" for candidate in candidates
                    ],
                },
                serialize=lambda result: {"decision": result.model_dump(mode="json")},
                rationale=lambda result: result.reasoning_summary,
                validation_checks=("pydantic_schema", "coordinator_business_rules"),
                llm_calls=coordinator_calls,
            )
        approved_ids = {action.action_id: action for action in decision.approved_actions}
        approved_for_site = [
            action.model_copy(update={"priority": approved_ids[action.action_id].priority})
            for action in candidates
            if action.action_id in approved_ids
        ]
        return site.site_id, evidence, approved_for_site

    # Provider calls are network-bound. Run independent live reef evaluations
    # concurrently so one slow reef does not hold every other reef hostage.
    # Offline fixtures stay sequential to preserve their deterministic trace.
    if offline_mode:
        site_results = [assess_and_decide(site) for site in sites]
    else:
        max_workers = min(4, len(sites)) or 1
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="reef-site",
        ) as executor:
            site_results = list(executor.map(assess_and_decide, sites))

    approved: list[EligibleAction] = []
    evidence_by_site: dict[str, FusedEvidence] = {}
    for site_id, evidence, approved_for_site in site_results:
        evidence_by_site[site_id] = evidence
        approved.extend(approved_for_site)

    scores = score_sites(sites)
    problem = build_problem(
        approved,
        scenario,
        scores,
        site_names={site.site_id: site.name for site in sites},
    )
    plan = trace_recorder.record(
        TraceStage.OPTIMIZER,
        TraceExecutor.OPTIMIZER,
        lambda: solve(problem).model_copy(update={"replan_trigger": replan_trigger}),
        inputs={
            "scenario_ref": scenario.scenario_id,
            "candidate_action_refs": [
                f"{action.site_id}:{action.action_id}" for action in approved
            ],
            "site_scores": {score.site_id: score.model_dump(mode="json") for score in scores},
        },
        serialize=lambda result: {
            "plan_id": result.plan_id,
            "assignment_refs": [
                f"{assignment.site_id}:{assignment.action_id}" for assignment in result.assignments
            ],
            "deferred_site_ids": [site.site_id for site in result.deferred],
            "binding_constraints": result.binding_constraints,
            "total_strategic_value": result.total_strategic_value,
        },
        rationale=lambda result: (
            f"Selected {len(result.assignments)} feasible assignment(s) and deferred "
            f"{len(result.deferred)} site(s) under the simulated resource constraints."
        ),
        validation_checks=("or_tools_solution", "resource_constraints"),
    )
    execution_trace = trace_recorder.finalize(plan.plan_id)
    remember_state(
        plan,
        problem,
        site_ids,
        structured,
        evidence_by_site,
        offline_mode,
        execution_trace,
    )
    return plan
