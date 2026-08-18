'use client';

import { Panel } from '@/components';
import { useCurrentPlan } from '@/hooks/usePlan';
import { useSiteTrace } from '@/hooks/useTrace';
import { cx } from '@/lib/cx';
import type { TraceStep } from '@/types';

import styles from './CoordinatorTrace.module.css';

/**
 * The execution trace for one site, as a timestamped log.
 *
 * This is what actually ran, read from `GET /plan/{plan_id}/trace/{site_id}`:
 * every stage, in order, with its real start time, real latency, and the
 * rationale that stage produced. Nothing here is composed in the frontend.
 *
 * What this is not: a stream of the model's private chain of thought. The
 * backend records a stage only after it returns a validated result, and the
 * trace deliberately excludes raw prompts and token-by-token reasoning. So the
 * honest thing to show is the stage-by-stage record plus, for stages an LLM
 * actually ran, the provider, model, retry count and token usage.
 *
 * Stage labels say plainly whether a stage was deterministic, an LLM call, or
 * an offline fixture. A fixture must never read as reasoning.
 */

const STAGE_LABEL: Record<string, string> = {
  evidence_tools: 'Evidence tools queried',
  thermal_investigator: 'Thermal evidence assessed',
  disease_investigator: 'Disease evidence assessed',
  runoff_investigator: 'Runoff evidence assessed',
  physical_investigator: 'Physical damage assessed',
  evidence_fusion: 'Evidence fused',
  policy_eligibility: 'Policy eligibility resolved',
  coordinator: 'Coordinator decided',
  optimizer: 'Resources allocated',
};

const EXECUTOR_LABEL: Record<string, string> = {
  deterministic: 'Deterministic',
  llm: 'LLM',
  fixture: 'Fixture',
  optimizer: 'Optimizer',
};

function clockTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function StepRow({ step }: { step: TraceStep }) {
  const failed = step.status === 'failed';
  const isLlm = step.executor === 'llm';
  const tokens = step.token_usage;

  return (
    <li className={styles.item}>
      <span
        className={cx(
          styles.dot,
          failed && styles.dotFailed,
          isLlm && styles.dotLlm,
          step.executor === 'fixture' && styles.dotFixture,
        )}
        aria-hidden="true"
      />
      <div className={styles.body}>
        <div className={styles.headline}>
          <span className={styles.stage}>{STAGE_LABEL[step.stage] ?? step.stage}</span>
          <span
            className={cx(
              styles.executor,
              isLlm && styles.executorLlm,
              step.executor === 'fixture' && styles.executorFixture,
            )}
          >
            {EXECUTOR_LABEL[step.executor] ?? step.executor}
          </span>
          {failed ? <span className={styles.failed}>failed</span> : null}
        </div>

        {step.rationale ? <p className={styles.rationale}>{step.rationale}</p> : null}

        {failed && step.error_message ? (
          <p className={styles.errorText}>
            {step.error_type}: {step.error_message}
          </p>
        ) : null}

        <div className={styles.meta}>
          <span>{clockTime(step.started_at)}</span>
          <span>{step.latency_ms} ms</span>
          {isLlm && step.provider ? (
            <span>
              {step.provider}
              {step.model ? ` / ${step.model}` : ''}
            </span>
          ) : null}
          {isLlm && step.attempt_count && step.attempt_count > 1 ? (
            <span className={styles.retry}>
              {step.attempt_count} attempts, schema validation retried
            </span>
          ) : null}
          {tokens ? (
            <span>
              {tokens.input_tokens} in / {tokens.output_tokens} out tokens
            </span>
          ) : null}
          {(step.validation_checks ?? []).length > 0 ? (
            <span className={styles.checks}>
              validated: {(step.validation_checks ?? []).join(', ')}
            </span>
          ) : null}
        </div>
      </div>
    </li>
  );
}

export function CoordinatorTrace({ siteId }: { siteId: string }) {
  const { data: plan } = useCurrentPlan();
  const { data: trace, isPending, error } = useSiteTrace(plan?.plan_id ?? null, siteId);

  if (isPending) {
    return (
      <Panel title="Coordinator Agent - validated trace">
        <p className={styles.muted}>Loading the trace...</p>
      </Panel>
    );
  }

  if (error || !trace) {
    return (
      <Panel title="Coordinator Agent - validated trace">
        <p className={styles.muted}>
          No trace is retained for this plan. Traces are held in process, so a backend restart drops
          them.
        </p>
      </Panel>
    );
  }

  const steps = trace.steps;
  const llmSteps = steps.filter((step) => step.executor === 'llm');
  const totalMs = steps.reduce((sum, step) => sum + step.latency_ms, 0);
  const totalTokens = llmSteps.reduce(
    (sum, step) =>
      sum + (step.token_usage?.input_tokens ?? 0) + (step.token_usage?.output_tokens ?? 0),
    0,
  );

  return (
    <Panel
      title="Coordinator Agent - validated trace"
      hint={
        llmSteps.length > 0
          ? `${llmSteps.length} model call(s), ${totalTokens} tokens, ${totalMs} ms total`
          : `${steps.length} stages, ${totalMs} ms total, no model call`
      }
    >
      <ol className={styles.list} tabIndex={0} aria-label="Coordinator execution stages">
        {steps.map((step) => (
          <StepRow key={`${step.sequence}-${step.stage}`} step={step} />
        ))}
      </ol>

      {llmSteps.length === 0 ? (
        <div className={styles.notice}>
          <span aria-hidden="true">▲</span>
          <div>
            <strong>No model was called for this plan.</strong> The pipeline ran in offline demo
            mode, where the investigators and the Coordinator are deterministic fixtures. Use Run
            live diagnosis above to call the configured provider.
          </div>
        </div>
      ) : null}

      <p className={styles.footnote}>
        This is the record of what ran, not the model&apos;s internal reasoning. The backend records
        a stage after it returns a validated result, and the trace deliberately excludes raw prompts
        and token-by-token output.
      </p>
    </Panel>
  );
}
