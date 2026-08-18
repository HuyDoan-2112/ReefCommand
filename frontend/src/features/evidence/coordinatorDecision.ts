import type { SiteExecutionTrace, TraceStep } from '@/types';

/**
 * Read the Coordinator's decision out of an execution trace.
 *
 * `GET /sites/{site_id}/evidence` returns the fused support scores but carries
 * no Coordinator block, despite docs/api_requirements.md describing one. The
 * decision is only exposed through the trace, whose coordinator step holds the
 * complete validated object.
 *
 * The step's `output` is typed `JsonValue` on the wire, so it is narrowed here
 * with runtime checks rather than asserted. A trace that does not carry a
 * usable decision returns null and the surface says the decision is
 * unavailable, instead of rendering a half-built claim about what the
 * Coordinator concluded.
 */

export interface EvidenceRequest {
  type: string;
  priority: number;
  rationale: string;
}

export interface ApprovedAction {
  action_id: string;
  priority: string;
  rationale: string;
}

export interface CoordinatorDecision {
  evidence_sufficient: boolean;
  additional_evidence_needed: boolean;
  next_evidence: EvidenceRequest[];
  approved_actions: ApprovedAction[];
  reasoning_summary: string;
  /** What actually ran this stage: an LLM, or the offline fixture. */
  executor: string;
  provider: string | null;
  model: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readEvidenceRequests(value: unknown): EvidenceRequest[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (!isRecord(entry)) return [];
    const { type, priority, rationale } = entry;
    if (typeof type !== 'string') return [];
    return [
      {
        type,
        priority: typeof priority === 'number' ? priority : 0,
        rationale: typeof rationale === 'string' ? rationale : '',
      },
    ];
  });
}

function readApprovedActions(value: unknown): ApprovedAction[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((entry) => {
    if (!isRecord(entry)) return [];
    const { action_id, priority, rationale } = entry;
    if (typeof action_id !== 'string') return [];
    return [
      {
        action_id,
        priority: typeof priority === 'string' ? priority : 'medium',
        rationale: typeof rationale === 'string' ? rationale : '',
      },
    ];
  });
}

export function coordinatorStep(trace: SiteExecutionTrace | undefined): TraceStep | undefined {
  return trace?.steps.find((step) => step.stage === 'coordinator');
}

export function readCoordinatorDecision(
  trace: SiteExecutionTrace | undefined,
): CoordinatorDecision | null {
  const step = coordinatorStep(trace);
  if (!step) return null;

  const decision = step.output?.['decision'];
  if (!isRecord(decision)) return null;

  const {
    evidence_sufficient,
    additional_evidence_needed,
    next_evidence,
    approved_actions,
    reasoning_summary,
  } = decision;

  if (typeof evidence_sufficient !== 'boolean' || typeof additional_evidence_needed !== 'boolean') {
    return null;
  }

  return {
    evidence_sufficient,
    additional_evidence_needed,
    next_evidence: readEvidenceRequests(next_evidence),
    approved_actions: readApprovedActions(approved_actions),
    reasoning_summary: typeof reasoning_summary === 'string' ? reasoning_summary : '',
    executor: step.executor,
    provider: step.provider ?? null,
    model: step.model ?? null,
  };
}

/** Turn an evidence-request enum value into something a diver would be asked for. */
export function evidenceRequestLabel(type: string): string {
  const labels: Record<string, string> = {
    close_range_lesion_image: 'Close-range lesion imagery',
    repeat_dive_comparison: 'A repeat dive compared against the last survey',
    turbidity_reading: 'A turbidity reading',
    structural_damage_survey: 'A structural damage survey',
    water_sample: 'A water sample',
    photo_transect: 'A photo transect',
  };
  return labels[type] ?? type.replace(/_/g, ' ');
}
