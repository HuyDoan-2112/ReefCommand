/**
 * Types mirroring the backend Pydantic models.
 *
 * The naming is deliberate and should not be "simplified" in the UI layer.
 * `support` is a support score, not a probability. The four values do not sum to
 * 1 and the causes are not assumed independent, so do not render them as a
 * pie chart or as percentages of a whole.
 */

export type Cause = 'thermal' | 'disease' | 'runoff' | 'physical';

export type Provenance = 'live' | 'cache' | 'simulated' | 'synthetic';

export type Priority = 'low' | 'medium' | 'high';

export interface EvidenceCitation {
  source: string;
  reference: string | null;
  observedAt: string | null;
  reviewStatus: string | null;
  reportingOrganization: string | null;
  provenance: Provenance;
}

export interface CauseEvidence {
  cause: Cause;
  support: number;
  confidence: number;
  rationale: string;
  citations: EvidenceCitation[];
}

export interface FusedEvidence {
  siteId: string;
  byCause: Record<Cause, CauseEvidence>;
  dominantCauses: Cause[];
  ambiguity: number;
  lowestConfidence: number;
}

export interface SiteScores {
  siteId: string;
  ecologicalValue: number;
  strategicValue: number;
  weightsArePrototypeAssumptions: boolean;
}

export interface Assignment {
  siteId: string;
  siteName: string;
  actionId: string;
  actionClass: string;
  boatId: string | null;
  teamId: string | null;
  priority: Priority;
  estimatedHours: number;
  estimatedCostUsd: number;
  evidenceSummary: string;
  remainingUncertainty: string;
  compatibilityRationale: string;
  requiresManagerApproval: boolean;
}

export interface DeferredSite {
  siteId: string;
  siteName: string;
  fallbackActionId: string | null;
  reason: string;
}

export interface ResponsePlan {
  planId: string;
  generatedAt: string;
  scenarioId: string;
  scenarioBanner: string;
  assignments: Assignment[];
  deferred: DeferredSite[];
  totalStrategicValue: number;
  bindingConstraints: string[];
  replanTrigger: string | null;
  replanLatencyMs: number | null;
}
