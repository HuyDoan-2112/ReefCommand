/**
 * Domain type aliases over the generated OpenAPI schema.
 *
 * `api.ts` is generated from `openapi.json` and must never be edited by hand.
 * This file is the ergonomic surface the feature code imports from, so a
 * component reads `Assignment` rather than
 * `components['schemas']['Assignment']`.
 *
 * The naming is deliberate and should not be "simplified" in the UI layer.
 * `support` is a support score, not a probability. The four values do not sum
 * to 1 and the causes are not assumed independent, so do not render them as a
 * pie chart, a stacked bar, or percentages of a whole.
 *
 * Field names are snake_case because that is the wire format. There is no
 * camelCase mapping layer on purpose: a second naming convention is a second
 * place for the contract to drift.
 */

import type { components } from '@/types/api';

type Schemas = components['schemas'];

/** The four competing, non-mutually-exclusive cause hypotheses. */
export type Cause = Schemas['Cause'];

/** Where a value came from. Must be visible wherever the value is shown. */
export type Provenance = Schemas['Provenance'];

export type Priority = Schemas['Priority'];
export type ActionClass = Schemas['ActionClass'];
export type MonitoringProgram = Schemas['MonitoringProgram'];

export type ProvenanceMetadata = Schemas['ProvenanceMetadata'];

/** One cited source behind a support score, with its own provenance. */
export type EvidenceCitation = Schemas['EvidenceCitation'];

/** One cause's support and confidence. Always render the two together. */
export type CauseEvidence = Schemas['CauseEvidence'];

/** The four support scores for one site, reconciled but never normalized. */
export type FusedEvidence = Schemas['FusedEvidence'];

export type SiteScores = Schemas['SiteScores'];
export type SiteLocation = Schemas['SiteLocation'];
export type EcologicalMeasurements = Schemas['EcologicalMeasurements'];
export type SamplingMetadata = Schemas['SamplingMetadata'];
export type RestorationInvestment = Schemas['RestorationInvestment'];

/** A study-area site with its scores and its standing in the current plan. */
export type SiteView = Schemas['SiteView'];

export type Assignment = Schemas['Assignment'];
export type DeferredSite = Schemas['DeferredSite'];

/** The operations plan. `scenario_banner` rides on it so it cannot be dropped. */
export type ResponsePlan = Schemas['ResponsePlan'];

export type Boat = Schemas['Boat'];
export type DiveTeam = Schemas['DiveTeam'];
export type Inventory = Schemas['Inventory'];
export type ResourceScenario = Schemas['ResourceScenario'];
export type ScenarioView = Schemas['ScenarioView'];
export type ResourceChangeResult = Schemas['ResourceChangeResult'];
export type ResourceChangeRequest = Schemas['ResourceChangeRequest'];

export type FieldReport = Schemas['FieldReport'];
export type StructuredObservation = Schemas['StructuredObservation'];
export type ReportStructureResult = Schemas['ReportStructureResult'];
export type StructuredObservationSubmission = Schemas['StructuredObservationSubmission'];
export type ObservationAccepted = Schemas['ObservationAccepted'];
export type RecomputeRequest = Schemas['RecomputeRequest'];

export type DataSourceStatus = Schemas['DataSourceStatus'];
export type DataSourcesHealth = Schemas['DataSourcesHealth'];
export type HealthStatus = Schemas['HealthStatus'];

/** Redacted execution trace for one completed plan. */
export type ExecutionTrace = Schemas['ExecutionTrace'];
export type SiteExecutionTrace = Schemas['SiteExecutionTrace'];
export type TraceStep = Schemas['TraceStep'];
export type TraceStage = Schemas['TraceStage'];
export type TraceExecutor = Schemas['TraceExecutor'];
export type TraceStatus = Schemas['TraceStatus'];
export type TokenUsage = Schemas['TokenUsage'];

/**
 * The four causes in a fixed display order.
 *
 * Fixed so that a site's bars do not reorder between renders or between sites,
 * which would make two sites impossible to compare at a glance.
 */
export const CAUSES: readonly Cause[] = ['thermal', 'disease', 'runoff', 'physical'] as const;
