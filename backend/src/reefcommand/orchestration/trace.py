"""Typed, redacted execution traces for completed planning runs.

The trace records structured inputs and outputs at each architectural boundary.
It deliberately does not store prompts, authorization headers, API keys, or a
model's private token-by-token reasoning.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from time import perf_counter

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, model_validator

from reefcommand.llm.client import LlmCallMetrics


class TraceStage(StrEnum):
    """Named stages visible to API clients and the future dashboard."""

    EVIDENCE_TOOLS = "evidence_tools"
    THERMAL_INVESTIGATOR = "thermal_investigator"
    DISEASE_INVESTIGATOR = "disease_investigator"
    RUNOFF_INVESTIGATOR = "runoff_investigator"
    PHYSICAL_INVESTIGATOR = "physical_investigator"
    EVIDENCE_FUSION = "evidence_fusion"
    POLICY_ELIGIBILITY = "policy_eligibility"
    COORDINATOR = "coordinator"
    OPTIMIZER = "optimizer"


class TraceExecutor(StrEnum):
    """What actually executed a trace stage."""

    DETERMINISTIC = "deterministic"
    LLM = "llm"
    FIXTURE = "fixture"
    OPTIMIZER = "optimizer"


class TokenUsage(BaseModel):
    """Provider-reported token usage accumulated across validation retries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


class TraceStep(BaseModel):
    """One completed and validated pipeline boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=1)
    stage: TraceStage
    executor: TraceExecutor
    site_id: str | None = None
    started_at: AwareDatetime
    completed_at: AwareDatetime
    latency_ms: int = Field(ge=0)
    provider: str | None = None
    model: str | None = None
    attempt_count: int | None = Field(default=None, ge=1)
    token_usage: TokenUsage | None = None
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    output: dict[str, JsonValue] = Field(default_factory=dict)
    rationale: str | None = None
    validation_checks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing_and_provider(self) -> TraceStep:
        if self.completed_at < self.started_at:
            raise ValueError("trace step completed_at must not precede started_at")
        if self.executor is TraceExecutor.LLM and (not self.provider or not self.model):
            raise ValueError("live LLM trace steps require provider and model")
        if self.executor is not TraceExecutor.LLM and self.token_usage is not None:
            raise ValueError("only live LLM trace steps may carry token usage")
        return self


class ExecutionTrace(BaseModel):
    """Complete trace retained for one response plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str = Field(min_length=1)
    parent_plan_id: str | None = None
    scenario_id: str = Field(min_length=1)
    trigger: str | None = None
    offline: bool
    started_at: AwareDatetime
    completed_at: AwareDatetime
    latency_ms: int = Field(ge=0)
    steps: list[TraceStep]

    @model_validator(mode="after")
    def validate_sequence(self) -> ExecutionTrace:
        expected = list(range(1, len(self.steps) + 1))
        actual = [step.sequence for step in self.steps]
        if actual != expected:
            raise ValueError("trace step sequence must be contiguous and ordered")
        if self.completed_at < self.started_at:
            raise ValueError("trace completed_at must not precede started_at")
        return self


class SiteExecutionTrace(BaseModel):
    """Site-filtered view of a completed execution trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    plan_id: str
    parent_plan_id: str | None = None
    scenario_id: str
    trigger: str | None = None
    offline: bool
    site_id: str
    steps: list[TraceStep]


class TraceRecorder:
    """Mutable run-local recorder that emits immutable API models."""

    def __init__(self, scenario_id: str, *, offline: bool, trigger: str | None = None) -> None:
        self.scenario_id = scenario_id
        self.offline = offline
        self.trigger = trigger
        self.started_at = datetime.now(UTC)
        self._started_clock = perf_counter()
        self._steps: list[TraceStep] = []

    def record[ResultT](
        self,
        stage: TraceStage,
        executor: TraceExecutor,
        operation: Callable[[], ResultT],
        *,
        inputs: dict[str, JsonValue] | None = None,
        serialize: Callable[[ResultT], dict[str, JsonValue]],
        rationale: Callable[[ResultT], str | None] | None = None,
        site_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        validation_checks: Sequence[str] = (),
        llm_calls: Sequence[LlmCallMetrics] | None = None,
    ) -> ResultT:
        """Execute one stage and append a redacted trace after it succeeds."""
        started_at = datetime.now(UTC)
        started_clock = perf_counter()
        result = operation()
        completed_at = datetime.now(UTC)
        latency_ms = max(0, round((perf_counter() - started_clock) * 1000))
        calls = list(llm_calls or [])
        token_usage = None
        attempt_count = None
        if calls:
            attempt_count = sum(call.attempt_count for call in calls)
            if any(
                call.input_tokens is not None or call.output_tokens is not None for call in calls
            ):
                token_usage = TokenUsage(
                    input_tokens=sum(call.input_tokens or 0 for call in calls),
                    output_tokens=sum(call.output_tokens or 0 for call in calls),
                )
        self._steps.append(
            TraceStep(
                sequence=len(self._steps) + 1,
                stage=stage,
                executor=executor,
                site_id=site_id,
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=latency_ms,
                provider=provider,
                model=model,
                attempt_count=attempt_count,
                token_usage=token_usage,
                inputs=inputs or {},
                output=serialize(result),
                rationale=rationale(result) if rationale else None,
                validation_checks=list(validation_checks),
            )
        )
        return result

    def finalize(self, plan_id: str, *, parent_plan_id: str | None = None) -> ExecutionTrace:
        """Freeze the completed run under the plan id returned by the optimizer."""
        completed_at = datetime.now(UTC)
        return ExecutionTrace(
            plan_id=plan_id,
            parent_plan_id=parent_plan_id,
            scenario_id=self.scenario_id,
            trigger=self.trigger,
            offline=self.offline,
            started_at=self.started_at,
            completed_at=completed_at,
            latency_ms=max(0, round((perf_counter() - self._started_clock) * 1000)),
            steps=list(self._steps),
        )


def for_site(trace: ExecutionTrace, site_id: str) -> SiteExecutionTrace:
    """Return site stages plus plan-wide stages such as the optimizer."""
    steps = [step for step in trace.steps if step.site_id in (None, site_id)]
    if not any(step.site_id == site_id for step in steps):
        raise KeyError(site_id)
    return SiteExecutionTrace(
        plan_id=trace.plan_id,
        parent_plan_id=trace.parent_plan_id,
        scenario_id=trace.scenario_id,
        trigger=trace.trigger,
        offline=trace.offline,
        site_id=site_id,
        steps=steps,
    )
