"""Typed, redacted execution traces for completed planning runs.

The trace records structured inputs and outputs at each architectural boundary.
It deliberately does not store prompts, authorization headers, API keys, or a
model's private token-by-token reasoning.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from time import perf_counter
from uuid import uuid4

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


class TraceStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


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
    status: TraceStatus = TraceStatus.SUCCEEDED
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
    error_type: str | None = None
    error_message: str | None = None
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
        if self.status is TraceStatus.FAILED and not self.error_type:
            raise ValueError("failed trace steps require an error_type")
        if self.status is TraceStatus.SUCCEEDED and (self.error_type or self.error_message):
            raise ValueError("successful trace steps cannot carry error details")
        return self


class ExecutionTrace(BaseModel):
    """Complete trace retained for one response plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str = Field(min_length=1)
    plan_id: str | None = None
    status: TraceStatus = TraceStatus.SUCCEEDED
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
        if self.status is TraceStatus.SUCCEEDED and not self.plan_id:
            raise ValueError("successful execution traces require a plan_id")
        return self


class SiteExecutionTrace(BaseModel):
    """Site-filtered view of a completed execution trace."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str
    plan_id: str
    status: TraceStatus
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
        self.trace_id = f"trace-{uuid4().hex[:12]}"
        self.offline = offline
        self.trigger = trigger
        self.started_at = datetime.now(UTC)
        self._started_clock = perf_counter()
        self._steps: list[TraceStep] = []
        self._steps_lock = RLock()

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
        try:
            result = operation()
        except Exception as exc:
            completed_at = datetime.now(UTC)
            with self._steps_lock:
                self._steps.append(
                    TraceStep(
                        sequence=len(self._steps) + 1,
                        stage=stage,
                        executor=executor,
                        status=TraceStatus.FAILED,
                        site_id=site_id,
                        started_at=started_at,
                        completed_at=completed_at,
                        latency_ms=max(0, round((perf_counter() - started_clock) * 1000)),
                        provider=provider,
                        model=model,
                        inputs=inputs or {},
                        error_type=type(exc).__name__,
                        error_message="Stage failed before producing validated output.",
                        validation_checks=list(validation_checks),
                    )
                )
            _remember_failed_trace(self.finalize(None, status=TraceStatus.FAILED))
            exc.add_note(f"ReefCommand execution trace id: {self.trace_id}")
            raise
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
        with self._steps_lock:
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

    def finalize(
        self,
        plan_id: str | None,
        *,
        parent_plan_id: str | None = None,
        status: TraceStatus = TraceStatus.SUCCEEDED,
    ) -> ExecutionTrace:
        """Freeze the completed run under the plan id returned by the optimizer."""
        completed_at = datetime.now(UTC)
        with self._steps_lock:
            steps = list(self._steps)
        return ExecutionTrace(
            trace_id=self.trace_id,
            plan_id=plan_id,
            status=status,
            parent_plan_id=parent_plan_id,
            scenario_id=self.scenario_id,
            trigger=self.trigger,
            offline=self.offline,
            started_at=self.started_at,
            completed_at=completed_at,
            latency_ms=max(0, round((perf_counter() - self._started_clock) * 1000)),
            steps=steps,
        )


def for_site(trace: ExecutionTrace, site_id: str) -> SiteExecutionTrace:
    """Return site stages plus plan-wide stages such as the optimizer."""
    steps = [step for step in trace.steps if step.site_id in (None, site_id)]
    if not any(step.site_id == site_id for step in steps):
        raise KeyError(site_id)
    return SiteExecutionTrace(
        trace_id=trace.trace_id,
        plan_id=trace.plan_id or trace.trace_id,
        status=trace.status,
        parent_plan_id=trace.parent_plan_id,
        scenario_id=trace.scenario_id,
        trigger=trace.trigger,
        offline=trace.offline,
        site_id=site_id,
        steps=steps,
    )


_FAILED_TRACE_LIMIT = 8
_FAILED_TRACES: OrderedDict[str, ExecutionTrace] = OrderedDict()
_FAILED_TRACE_LOCK = RLock()


def _remember_failed_trace(trace: ExecutionTrace) -> None:
    with _FAILED_TRACE_LOCK:
        _FAILED_TRACES[trace.trace_id] = trace
        while len(_FAILED_TRACES) > _FAILED_TRACE_LIMIT:
            _FAILED_TRACES.popitem(last=False)


def failed_trace_for_id(trace_id: str) -> ExecutionTrace | None:
    """Return one bounded failed-run trace for debugging."""
    with _FAILED_TRACE_LOCK:
        return _FAILED_TRACES.get(trace_id)
