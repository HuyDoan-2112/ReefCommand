/**
 * One typed function per backend endpoint.
 *
 * Feature code calls hooks, hooks call these, and only these know the URL
 * shapes. Response types come from the generated schema, so a backend contract
 * change surfaces here as a type error rather than as a runtime surprise in a
 * component.
 */

import { get, patch, post } from '@/api/client';
import type {
  DataSourcesHealth,
  ExecutionTrace,
  FieldReport,
  FusedEvidence,
  ObservationAccepted,
  RecomputeRequest,
  ResourceChangeRequest,
  ResourceChangeResult,
  ResponsePlan,
  ScenarioView,
  SiteExecutionTrace,
  SiteView,
} from '@/types';

/** The current response plan. Never starts a planning run of its own. */
export function fetchCurrentPlan(): Promise<ResponsePlan> {
  return get<ResponsePlan>('/plan/current');
}

/** All study-area sites with both value scores and their standing in the plan. */
export function fetchSites(): Promise<SiteView[]> {
  return get<SiteView[]>('/sites');
}

/** Fused evidence for one site: four support scores, confidence, citations. */
export function fetchSiteEvidence(siteId: string): Promise<FusedEvidence> {
  return get<FusedEvidence>(`/sites/${encodeURIComponent(siteId)}/evidence`);
}

/** The active simulated capacity scenario and its mandatory banner. */
export function fetchScenario(): Promise<ScenarioView> {
  return get<ScenarioView>('/resources/scenario');
}

/** Per-source live-versus-cache standing behind the current plan. */
export function fetchDataSources(): Promise<DataSourcesHealth> {
  return get<DataSourcesHealth>('/health/data-sources');
}

/**
 * The redacted execution trace for one plan.
 *
 * This is where the Coordinator's decision lives, including any request for
 * additional evidence. `GET /sites/{id}/evidence` carries the fused scores but
 * not the Coordinator block, so the evidence surface reads both.
 */
export function fetchExecutionTrace(planId: string): Promise<ExecutionTrace> {
  return get<ExecutionTrace>(`/plan/${encodeURIComponent(planId)}/trace`);
}

/** Site stages from the same trace, plus plan-wide stages such as the optimizer. */
export function fetchSiteTrace(planId: string, siteId: string): Promise<SiteExecutionTrace> {
  return get<SiteExecutionTrace>(
    `/plan/${encodeURIComponent(planId)}/trace/${encodeURIComponent(siteId)}`,
  );
}

/** Submit a field report. This is the primary re-planning trigger. */
export function submitObservation(report: FieldReport): Promise<ObservationAccepted> {
  return post<ObservationAccepted>('/observations', report);
}

/** Change the capacity scenario, which re-runs the optimizer only. */
export function changeScenario(body: ResourceChangeRequest): Promise<ResourceChangeResult> {
  return patch<ResourceChangeResult>('/resources/scenario', body);
}

/** Force a recompute. Useful for the demo and for debugging. */
export function recomputePlan(body?: RecomputeRequest): Promise<ResponsePlan> {
  return post<ResponsePlan>('/plan/recompute', body);
}
