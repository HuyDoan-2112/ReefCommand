"""Field observation intake.

Submitting a report is the demo's re-planning trigger, so this endpoint returns
the id of the plan recompute it started along with a timestamp, letting the
dashboard measure and display responsiveness.
"""

from __future__ import annotations

import os
from time import perf_counter

from fastapi import APIRouter, HTTPException

from reefcommand.api import state
from reefcommand.api.schemas import (
    ObservationAccepted,
    ReportStructureResult,
    StructuredObservationSubmission,
)
from reefcommand.config import get_settings
from reefcommand.domain.observation import FieldReport
from reefcommand.ingestion.llm_field_reports import structure_live
from reefcommand.llm.client import collect_llm_calls

router = APIRouter(prefix="/observations", tags=["observations"])


def _require_live_credential() -> None:
    settings = get_settings()
    has_credential = (
        bool(settings.deepseek_api_key and settings.deepseek_api_key.strip())
        if settings.llm_provider == "deepseek"
        else bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    )
    if has_credential:
        return
    credential = (
        "REEFCOMMAND_DEEPSEEK_API_KEY"
        if settings.llm_provider == "deepseek"
        else "ANTHROPIC_API_KEY"
    )
    raise HTTPException(
        status_code=409,
        detail=f"Live report structuring requires {credential}.",
    )


@router.post("/structure", response_model=ReportStructureResult)
def structure_report(report: FieldReport) -> ReportStructureResult:
    """Use the configured LLM to convert messy report text into a validated observation."""
    _require_live_credential()
    started = perf_counter()
    try:
        with collect_llm_calls() as calls:
            extraction = structure_live(report)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not calls:
        raise HTTPException(status_code=502, detail="The provider returned no call metadata.")
    metrics = calls[-1]
    return ReportStructureResult(
        report_id=report.report_id,
        observation=extraction.observation,
        extraction_confidence=extraction.extraction_confidence,
        provider=metrics.provider,
        model=metrics.model,
        attempt_count=metrics.attempt_count,
        input_tokens=metrics.input_tokens,
        output_tokens=metrics.output_tokens,
        latency_ms=max(0, int((perf_counter() - started) * 1000)),
    )


@router.post("", response_model=ObservationAccepted)
def submit_observation(report: FieldReport) -> ObservationAccepted:
    """Accept a field report, structure it, and trigger re-planning."""
    try:
        plan = state.apply_observation(report)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ObservationAccepted(
        report_id=report.report_id,
        plan=plan,
        replan_latency_ms=plan.replan_latency_ms,
    )


@router.post("/structured", response_model=ObservationAccepted)
def submit_structured_observation(
    submission: StructuredObservationSubmission,
) -> ObservationAccepted:
    """Accept a reviewed structured observation and trigger re-planning without another LLM call."""
    try:
        plan = state.apply_structured_observation(
            submission.report,
            submission.observation,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ObservationAccepted(
        report_id=submission.report.report_id,
        plan=plan,
        replan_latency_ms=plan.replan_latency_ms,
    )
