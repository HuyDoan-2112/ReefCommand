"""Execution trace contracts and live-provider metadata."""

from __future__ import annotations

from reefcommand.llm.client import LlmCallMetrics
from reefcommand.orchestration.trace import (
    TraceExecutor,
    TraceRecorder,
    TraceStage,
    for_site,
)


def test_live_agent_trace_records_redacted_metrics_and_site_view() -> None:
    recorder = TraceRecorder("demo_default", offline=False)
    calls = [
        LlmCallMetrics(
            provider="deepseek",
            model="deepseek-v4-flash",
            attempt_count=2,
            input_tokens=120,
            output_tokens=30,
        )
    ]
    recorder.record(
        TraceStage.DISEASE_INVESTIGATOR,
        TraceExecutor.LLM,
        lambda: {"support": 0.7},
        site_id="cheeca_rocks",
        provider="deepseek",
        model="deepseek-v4-flash",
        inputs={"observation_count": 1},
        serialize=lambda result: result,
        rationale=lambda _result: "Lesion evidence supports a disease investigation.",
        validation_checks=("pydantic_schema",),
        llm_calls=calls,
    )
    recorder.record(
        TraceStage.OPTIMIZER,
        TraceExecutor.OPTIMIZER,
        lambda: {"assignments": 1},
        inputs={"candidate_count": 1},
        serialize=lambda result: result,
        validation_checks=("resource_constraints",),
    )

    trace = recorder.finalize("plan-123")
    agent_step = trace.steps[0]

    assert agent_step.provider == "deepseek"
    assert agent_step.model == "deepseek-v4-flash"
    assert agent_step.attempt_count == 2
    assert agent_step.token_usage is not None
    assert agent_step.token_usage.input_tokens == 120
    assert agent_step.token_usage.output_tokens == 30
    assert "key" not in agent_step.model_dump_json().lower()
    assert [step.stage for step in for_site(trace, "cheeca_rocks").steps] == [
        TraceStage.DISEASE_INVESTIGATOR,
        TraceStage.OPTIMIZER,
    ]
