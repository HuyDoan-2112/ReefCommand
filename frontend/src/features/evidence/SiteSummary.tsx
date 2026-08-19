'use client';

import Link from 'next/link';
import type { CSSProperties } from 'react';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { Button, ConditionBadge, type Condition } from '@/components';
import {
  useBaselinePlan,
  useCurrentPlan,
  useLatestSitePlan,
  useRecomputePlan,
} from '@/hooks/usePlan';
import { useSiteEvidence, useSites } from '@/hooks/useSites';
import { useExecutionTrace } from '@/hooks/useTrace';
import type { FusedEvidence, ResponsePlan, SiteView } from '@/types';

import { CoordinatorTrace } from './CoordinatorTrace';
import { EvidencePanel } from './EvidencePanel';
import { RecommendedInterventions } from './RecommendedInterventions';

import styles from './SiteSummary.module.css';

function mutationMessage(error: Error | null): string | null {
  if (!error) return null;
  return error instanceof ApiError && error.detail ? error.detail : error.message;
}

function conditionForSite(site: SiteView): Condition {
  if (site.current_assignment?.priority === 'high') return 'critical';
  if (site.current_assignment) return 'serious';
  if (site.deferred) return 'warning';
  return 'good';
}

function reportCount(evidence: FusedEvidence | undefined): number {
  const citations = Object.values(evidence?.by_cause ?? {}).flatMap(
    (cause) => cause?.citations ?? [],
  );
  return new Set(
    citations
      .filter((citation) =>
        citation.source.toLowerCase().startsWith('structured form of demo report'),
      )
      .map((citation) => citation.reference ?? citation.source),
  ).size;
}

function latestSurveyYear(site: SiteView): number | null {
  return [...site.measurements.sampling.reference_years].sort((a, b) => b - a)[0] ?? null;
}

function sampleLabel(site: SiteView): string {
  const { program, sample_n: sampleN, sample_unit: sampleUnit } = site.measurements.sampling;
  const unit = sampleUnit.replaceAll('_', ' ');
  return `${program} ${sampleN} ${unit}${sampleN === 1 ? '' : 's'}`;
}

function dhwLabel(evidence: FusedEvidence | undefined): string | null {
  const summary = evidence?.by_cause.thermal?.display_summary ?? '';
  const match = summary.match(/\bDHW\s+([\d.]+)/i);
  return match ? `DHW ${match[1]}` : null;
}

export function SiteSummary({ siteId }: { siteId: string }) {
  const { data: sites, isPending, error } = useSites();
  const { data: plan } = useCurrentPlan();
  const { data: baselinePlan } = useBaselinePlan();
  const { data: latestSitePlan } = useLatestSitePlan(siteId);
  const [livePlan, setLivePlan] = useState<ResponsePlan | null>(null);
  const recompute = useRecomputePlan();
  const displayedPlanId =
    livePlan?.plan_id ?? latestSitePlan?.plan_id ?? baselinePlan?.plan_id ?? null;
  const { data: siteEvidence } = useSiteEvidence(siteId, displayedPlanId);
  const { data: planTrace } = useExecutionTrace(displayedPlanId);

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
  const isLivePlan = planTrace?.offline === false && llmSteps.length > 0;
  const liveError = mutationMessage(recompute.error);
  const reports = reportCount(siteEvidence);
  const dhw = dhwLabel(siteEvidence);
  const surveyYear = latestSurveyYear(site);
  function runLivePipeline() {
    recompute.mutate(
      {
        scenario_id: plan?.scenario_id ?? 'demo_default',
        site_ids: [siteId],
        execution_mode: 'live_llm',
      },
      {
        onSuccess: setLivePlan,
      },
    );
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
            <ConditionBadge
              condition={conditionForSite(site)}
              basis="current response plan status"
            />
            {dhw ? <span className={styles.tag}>🌡️ {dhw}</span> : null}
            {reports > 0 ? (
              <span className={styles.tag}>
                🤿 {reports} report{reports === 1 ? '' : 's'} cited
              </span>
            ) : null}
            <span className={styles.tag}>🧪 {sampleLabel(site)}</span>
            {surveyYear ? <span className={styles.tag}>📅 reference {surveyYear}</span> : null}
            {!isLivePlan ? (
              <span className={styles.fixtureTag}>Deterministic fixture baseline</span>
            ) : null}
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
            {recompute.isPending ? 'Running live agents...' : 'Run live diagnosis for this site'}
          </Button>
          <span className={styles.liveStatus} aria-live="polite">
            {recompute.isPending
              ? `Running the validated pipeline for ${site.name}.`
              : isLivePlan
                ? `${llmSteps.length} validated model calls, ${tokenCount.toLocaleString('en-US')} tokens`
                : 'Click to call the configured LLM. No private chain-of-thought is displayed.'}
          </span>
          {liveError ? <span className={styles.liveError}>{liveError}</span> : null}
        </div>
      </header>

      <EvidencePanel siteId={site.site_id} planId={displayedPlanId} />

      <div className={styles.decisionGrid}>
        <CoordinatorTrace siteId={site.site_id} planId={displayedPlanId} />
        <RecommendedInterventions siteId={site.site_id} planId={displayedPlanId} />
      </div>
    </div>
  );
}
