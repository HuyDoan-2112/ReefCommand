'use client';

import Link from 'next/link';
import type { CSSProperties } from 'react';

import { ApiError } from '@/api/client';
import { Button, ProvenanceBadge } from '@/components';
import { useCurrentPlan, useRecomputePlan } from '@/hooks/usePlan';
import { useSites } from '@/hooks/useSites';
import { useExecutionTrace } from '@/hooks/useTrace';

import { CoordinatorTrace } from './CoordinatorTrace';
import { EvidencePanel } from './EvidencePanel';
import { RecommendedInterventions } from './RecommendedInterventions';

import styles from './SiteSummary.module.css';

function mutationMessage(error: Error | null): string | null {
  if (!error) return null;
  return error instanceof ApiError && error.detail ? error.detail : error.message;
}

export function SiteSummary({ siteId }: { siteId: string }) {
  const { data: sites, isPending, error } = useSites();
  const { data: plan } = useCurrentPlan();
  const recompute = useRecomputePlan();
  const { data: planTrace } = useExecutionTrace(plan?.plan_id ?? null);

  if (isPending) return <p className={styles.muted}>Loading site...</p>;
  if (error) return <p className={styles.muted}>Could not load sites: {error.message}</p>;

  const site = sites.find((candidate) => candidate.site_id === siteId);
  if (!site) {
    return (
      <p className={styles.muted}>
        No site called {siteId}. <Link href="/">Back to the Command Map</Link>.
      </p>
    );
  }

  const llmSteps = planTrace?.steps.filter((step) => step.executor === 'llm') ?? [];
  const tokenCount = llmSteps.reduce(
    (total, step) =>
      total + (step.token_usage?.input_tokens ?? 0) + (step.token_usage?.output_tokens ?? 0),
    0,
  );
  const provider = llmSteps[0];
  const isLivePlan = planTrace?.offline === false && llmSteps.length > 0;
  const liveError = mutationMessage(recompute.error);
  const siteIds = sites.map((candidate) => candidate.site_id);

  function runLivePipeline() {
    recompute.mutate({
      scenario_id: plan?.scenario_id ?? 'demo_default',
      site_ids: siteIds,
      execution_mode: 'live_llm',
    });
  }

  return (
    <div className={styles.root}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <div className={styles.eyebrow}>Site intelligence</div>
          <h2 className={styles.name}>{site.name}</h2>
          <div className={styles.coords}>
            {site.latitude.toFixed(4)}&deg; N, {Math.abs(site.longitude).toFixed(4)}&deg; W
            {site.location.zone_name_in_source ? ` (${site.location.zone_name_in_source})` : ''}
          </div>
          <div className={styles.headerTags}>
            <ProvenanceBadge
              provenance={site.location.provenance.kind}
              title={site.location.provenance.source}
            />
            {site.has_active_restoration ? (
              <span className={styles.tag}>Active restoration</span>
            ) : null}
            <span className={isLivePlan ? styles.liveTag : styles.fixtureTag}>
              {isLivePlan
                ? `${provider?.provider} ${provider?.model}`
                : 'Deterministic fixture baseline'}
            </span>
          </div>
        </div>

        <div className={styles.heroScores}>
          <div className={styles.heroScore}>
            <span
              className={styles.gauge}
              style={
                {
                  '--gauge-value': `${Math.round(site.scores.strategic_value * 100)}%`,
                } as CSSProperties
              }
            >
              <span>{site.scores.strategic_value.toFixed(2)}</span>
            </span>
            <span className={styles.heroScoreLabel}>Strategic value</span>
          </div>
          <div className={styles.heroScore}>
            <span
              className={styles.gaugeSecondary}
              style={
                {
                  '--gauge-value': `${Math.round(site.scores.ecological_value * 100)}%`,
                } as CSSProperties
              }
            >
              <span>{site.scores.ecological_value.toFixed(2)}</span>
            </span>
            <span className={styles.heroScoreLabel}>Ecological value</span>
          </div>
          {site.scores.weights_are_prototype_assumptions ? (
            <span className={styles.scoreAssumption}>Prototype weighting assumptions</span>
          ) : null}
        </div>

        <div className={styles.liveControl}>
          <Button variant="coral" onClick={runLivePipeline} disabled={recompute.isPending}>
            {recompute.isPending ? 'Running live agents...' : 'Run live diagnosis'}
          </Button>
          <span className={styles.liveStatus} aria-live="polite">
            {recompute.isPending
              ? `Running the validated pipeline for ${sites.length} sites. This can take a few minutes.`
              : isLivePlan
                ? `${llmSteps.length} validated model calls, ${tokenCount.toLocaleString('en-US')} tokens`
                : 'Click to call the configured LLM. No private chain-of-thought is displayed.'}
          </span>
          {liveError ? <span className={styles.liveError}>{liveError}</span> : null}
        </div>
      </header>

      <EvidencePanel siteId={site.site_id} />

      <div className={styles.decisionGrid}>
        <CoordinatorTrace siteId={site.site_id} />
        <RecommendedInterventions siteId={site.site_id} />
      </div>
    </div>
  );
}
