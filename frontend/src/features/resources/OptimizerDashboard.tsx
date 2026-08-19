'use client';

import { useMemo } from 'react';

import { Button, Panel, ProvenanceBadge, SimulatedDataBanner, StatTile } from '@/components';
import { useCurrentPlan, useRecomputePlan } from '@/hooks/usePlan';
import { useSites } from '@/hooks/useSites';
import { useScenario } from '@/hooks/useResources';
import { useExecutionTrace } from '@/hooks/useTrace';
import type {
  Assignment,
  ExecutionTrace,
  Priority,
  ResourceScenario,
  ResponsePlan,
  SiteView,
} from '@/types';

import styles from './OptimizerDashboard.module.css';

const PRIORITY_LABEL: Record<Priority, string> = {
  high: 'Critical',
  medium: 'Serious',
  low: 'Watch',
};

const ACTION_LABEL: Record<string, string> = {
  monitoring: 'Monitoring',
  intensive_monitoring: 'Intensive monitoring',
  physical_damage_assessment: 'Physical damage assessment',
  disease_assessment: 'Disease assessment',
  runoff_assessment: 'Runoff assessment',
};

function actionLabel(actionId: string): string {
  return ACTION_LABEL[actionId] ?? actionId.replace(/_/g, ' ');
}

function currency(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function causeLabel(summary: string): string {
  return summary.replace(/^Supporting causes:\s*/i, '').replace(/, /g, ' + ');
}

function siteLocation(site: SiteView | undefined): string {
  return site?.location.zone_name_in_source ?? 'Florida Keys';
}

function progress(value: number, maximum: number): string {
  if (maximum <= 0) return '0%';
  return `${Math.min(100, Math.max(0, (value / maximum) * 100))}%`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function coordinatorActionRefs(trace: ExecutionTrace | undefined): string[] {
  return (trace?.steps ?? []).flatMap((step) => {
    if (step.stage !== 'coordinator' || !step.output) return [];
    const decision = step.output.decision;
    if (!isRecord(decision) || !Array.isArray(decision.approved_actions)) return [];
    return decision.approved_actions.flatMap((action) => {
      if (!isRecord(action) || typeof action.action_id !== 'string') return [];
      return [`${step.site_id ?? 'site'}:${action.action_id}`];
    });
  });
}

function boatName(scenario: ResourceScenario, boatId: string | null | undefined): string {
  if (!boatId) return 'No boat';
  return scenario.boats.find((boat) => boat.boat_id === boatId)?.name ?? boatId;
}

function teamName(scenario: ResourceScenario, teamId: string | null | undefined): string {
  if (!teamId) return 'No team';
  return scenario.dive_teams.find((team) => team.team_id === teamId)?.name ?? teamId;
}

function actionCostByClass(plan: ResponsePlan): Array<{ label: string; value: number }> {
  const totals = new Map<string, number>();
  for (const assignment of plan.assignments) {
    totals.set(
      assignment.action_class,
      (totals.get(assignment.action_class) ?? 0) + assignment.estimated_cost_usd,
    );
  }
  return [...totals.entries()]
    .sort(([, left], [, right]) => right - left)
    .map(([label, value]) => ({ label: actionLabel(label), value }));
}

function AllocationRow({
  assignment,
  rank,
  scenario,
  site,
  maximumValue,
}: {
  assignment: Assignment;
  rank: number;
  scenario: ResourceScenario;
  site: SiteView | undefined;
  maximumValue: number;
}) {
  const value = site?.scores.strategic_value ?? 0;
  const equipment = assignment.equipment ?? [];
  return (
    <div className={styles.allocationRow}>
      <span className={styles.rank}>{rank}</span>
      <span className={styles.siteCell}>
        <strong>{assignment.site_name}</strong>
        <small>
          {siteLocation(site)} · {PRIORITY_LABEL[assignment.priority]}
        </small>
      </span>
      <span className={styles.cause}>{causeLabel(assignment.evidence_summary)}</span>
      <span className={styles.crewCell}>
        <span>{boatName(scenario, assignment.boat_id)}</span>
        <small>{teamName(scenario, assignment.team_id)}</small>
      </span>
      <span className={styles.equipmentCell}>
        <strong>{equipment.join(', ') || 'No dedicated equipment'}</strong>
        <small>{actionLabel(assignment.action_id)}</small>
      </span>
      <span className={styles.budgetCell}>{currency(assignment.estimated_cost_usd)}</span>
      <span className={styles.valueCell}>
        <span className={styles.valueTrack}>
          <span style={{ width: progress(value, maximumValue) }} />
        </span>
        <small>{value.toFixed(2)}</small>
      </span>
    </div>
  );
}

function DeferredRow({
  name,
  reason,
  rank,
  site,
  maximumValue,
}: {
  name: string;
  reason: string;
  rank: number;
  site: SiteView | undefined;
  maximumValue: number;
}) {
  const value = site?.scores.strategic_value ?? 0;
  return (
    <div className={`${styles.allocationRow} ${styles.deferredRow}`}>
      <span className={styles.rank}>{rank}</span>
      <span className={styles.siteCell}>
        <strong>{name}</strong>
        <small>{siteLocation(site)} · Deferred</small>
      </span>
      <span className={`${styles.cause} ${styles.causePending}`}>Deferred</span>
      <span className={styles.mutedCell}>-</span>
      <span className={styles.mutedCell}>No equipment</span>
      <span className={styles.mutedCell}>-</span>
      <span className={styles.valueCell}>
        <span className={styles.valueTrack}>
          <span style={{ width: progress(value, maximumValue) }} />
        </span>
        <small title={reason}>{value.toFixed(2)}</small>
      </span>
    </div>
  );
}

function ConstraintBar({
  label,
  value,
  maximum,
  display,
}: {
  label: string;
  value: number;
  maximum: number;
  display: string;
}) {
  return (
    <div className={styles.constraintRow}>
      <div className={styles.constraintLabel}>
        <span>{label}</span>
        <strong>{display}</strong>
      </div>
      <span className={styles.constraintTrack}>
        <span style={{ width: progress(value, maximum) }} />
      </span>
    </div>
  );
}

export function OptimizerDashboard() {
  const { data: plan, isPending: planPending, error: planError } = useCurrentPlan();
  const { data: scenarioView, isPending: scenarioPending, error: scenarioError } = useScenario();
  const { data: sites } = useSites();
  const recompute = useRecomputePlan();
  const { data: trace } = useExecutionTrace(plan?.plan_id ?? null);

  const siteById = useMemo(
    () => new Map((sites ?? []).map((site) => [site.site_id, site])),
    [sites],
  );
  const totalCost =
    plan?.assignments.reduce((sum, assignment) => sum + assignment.estimated_cost_usd, 0) ?? 0;
  const totalHours =
    plan?.assignments.reduce((sum, assignment) => sum + assignment.estimated_hours, 0) ?? 0;
  const actionCosts = plan ? actionCostByClass(plan) : [];
  const maxValue = Math.max(0.01, ...(sites ?? []).map((site) => site.scores.strategic_value));

  if (planPending || scenarioPending) {
    return <div className={styles.loading}>Loading the allocation plan...</div>;
  }
  if (planError || scenarioError || !plan || !scenarioView) {
    return (
      <div className={styles.error}>
        Could not load the optimizer:{' '}
        {planError?.message ?? scenarioError?.message ?? 'missing data'}
      </div>
    );
  }

  const scenario = scenarioView.scenario;
  const deferred = plan.deferred ?? [];
  const bindingConstraints = plan.binding_constraints ?? [];
  const availableBoats = scenario.boats.filter((boat) => boat.available !== false).length;
  const totalTeamHours = scenario.dive_teams.reduce((sum, team) => sum + team.available_hours, 0);
  const remainingBudget = Math.max(0, scenario.budget_usd - totalCost);
  const totalSites = plan.assignments.length + deferred.length;
  const allocationTotal = actionCosts.reduce((sum, item) => sum + item.value, 0);
  const scenarioId = plan.scenario_id;
  const equipmentSummary = (scenario.inventory.equipment ?? [])
    .map((item) => `${item.available_units} ${item.name.toLowerCase()}`)
    .join(' · ');
  const equipmentNote = (scenario.inventory.equipment ?? [])
    .map((item) => `${item.available_units} ${item.category}`)
    .join(' · ');
  const liveSteps = trace?.steps.filter((step) => step.executor === 'llm') ?? [];
  const liveProvider = liveSteps.find((step) => step.provider)?.provider;
  const liveModel = liveSteps.find((step) => step.model)?.model;
  const optimizerTrace = trace?.steps.find((step) => step.stage === 'optimizer');
  const approvedActionRefs = coordinatorActionRefs(trace);
  const assignmentRefs = stringArray(optimizerTrace?.output?.assignment_refs);
  const deferredSiteIds = stringArray(optimizerTrace?.output?.deferred_site_ids);
  const bindingTrace = stringArray(optimizerTrace?.output?.binding_constraints);
  const visibleActionRefs = approvedActionRefs.slice(0, 6);
  const isLiveResult = trace !== undefined && !trace.offline;
  const freshLiveRun = recompute.data?.plan_id === plan.plan_id && isLiveResult;
  const runStateLabel = recompute.isPending
    ? 'Live run in progress'
    : freshLiveRun
      ? 'Live run completed'
      : isLiveResult
        ? 'Current plan is live'
        : 'Default fixture baseline';

  function runLivePlan() {
    recompute.mutate({
      scenario_id: scenarioId,
      site_ids: sites?.map((site) => site.site_id),
      execution_mode: 'live_llm',
    });
  }

  return (
    <div className={styles.root}>
      <SimulatedDataBanner text={scenarioView.banner} detail={scenario.label} />

      <div className={styles.statRow}>
        <StatTile
          label="🛥️ Boats available"
          value={availableBoats}
          unit={`/ ${scenario.boats.length}`}
          note="simulated operating fleet"
          decoration="🛥️"
        />
        <StatTile
          label="🤿 Dive teams"
          value={scenario.dive_teams.length}
          unit={`/ ${totalTeamHours.toFixed(1)} h`}
          note="simulated team capacity"
          decoration="🤿"
        />
        <StatTile
          label="🧰 Equipment kits"
          value={
            scenario.inventory.shade_units +
            scenario.inventory.monitoring_kits +
            scenario.inventory.sampling_kits
          }
          note={
            <span title={equipmentSummary || 'Named equipment details unavailable'}>
              {equipmentNote || 'Named equipment details unavailable'}
            </span>
          }
          decoration="🧰"
        />
        <StatTile
          label="💵 Budget remaining"
          value={currency(remainingBudget)}
          unit={`/ ${currency(scenario.budget_usd)}`}
          note={<ProvenanceBadge provenance={scenario.provenance} />}
          decoration="💵"
        />
      </div>

      <div className={styles.agentCallout}>
        <span aria-hidden="true">🧠</span>
        <div className={styles.agentCopy}>
          <div className={styles.agentTitleRow}>
            <strong>Live demo control</strong>
            <span className={isLiveResult ? styles.liveMode : styles.fixtureMode}>
              {runStateLabel}
            </span>
          </div>
          <span>
            {trace && !trace.offline && liveSteps.length > 0
              ? `${liveSteps.length} validated ${liveProvider ?? 'LLM'} call(s) reviewed ${
                  sites?.length ?? 0
                } reef(s). The deterministic optimizer then assigned simulated resources.`
              : `The live Coordinator reviews all ${
                  sites?.length ?? 0
                } reefs before the deterministic optimizer assigns simulated resources under today&apos;s constraints.`}
          </span>
        </div>
        <Button variant="coral" disabled={recompute.isPending} onClick={runLivePlan}>
          {recompute.isPending ? 'Running live review...' : 'Run live review + optimize'}
        </Button>
      </div>

      <section className={styles.handoff} aria-label="Validated Coordinator handoff to OR-Tools">
        <div className={styles.handoffHead}>
          <strong>Validated Coordinator handoff</strong>
          <span>Structured output → OR-Tools</span>
        </div>
        <div className={styles.handoffFlow}>
          <div className={styles.handoffStage}>
            <span>Coordinator</span>
            <strong>{approvedActionRefs.length}</strong>
            <small>approved actions</small>
          </div>
          <span className={styles.handoffArrow} aria-hidden="true">
            →
          </span>
          <div className={styles.handoffStage}>
            <span>OR-Tools</span>
            <strong>{assignmentRefs.length}</strong>
            <small>assignments · {deferredSiteIds.length} deferred</small>
          </div>
        </div>
        <div className={styles.handoffDetails}>
          <span>
            {visibleActionRefs.join(' · ') || 'No approved actions in the current trace'}
            {approvedActionRefs.length > visibleActionRefs.length
              ? ` · +${approvedActionRefs.length - visibleActionRefs.length} more`
              : ''}
          </span>
          {bindingTrace.length > 0 ? <span>Constraint: {bindingTrace.join(', ')}</span> : null}
        </div>
      </section>

      {recompute.isError ? (
        <p className={styles.error}>Live run failed: {recompute.error.message}</p>
      ) : null}
      {recompute.isSuccess ? (
        <p className={styles.success}>
          {trace && !trace.offline
            ? `Live ${liveProvider ?? 'LLM'}${liveModel ? ` (${liveModel})` : ''} decisions were validated, then the deterministic allocation was recomputed.`
            : 'The live run completed. Refreshing its validated trace...'}
        </p>
      ) : null}

      <div className={styles.dashboardGrid}>
        <Panel
          className={styles.allocationPanel}
          title="📋 This Week's Allocation Plan"
          hint={`top ${plan.assignments.length} of ${totalSites} flagged sites, ranked by strategic value`}
          scrollX
        >
          <div className={styles.tableViewport}>
            <div className={styles.table}>
              <div className={`${styles.allocationRow} ${styles.tableHead}`}>
                <span>#</span>
                <span>Site</span>
                <span>Cause</span>
                <span>Boat / team</span>
                <span>Equipment</span>
                <span>Budget</span>
                <span>Strategic value</span>
              </div>
              {plan.assignments.map((assignment, index) => (
                <AllocationRow
                  key={`${assignment.site_id}-${assignment.action_id}`}
                  assignment={assignment}
                  rank={index + 1}
                  scenario={scenario}
                  site={siteById.get(assignment.site_id)}
                  maximumValue={maxValue}
                />
              ))}
              {deferred.map((site, index) => (
                <DeferredRow
                  key={site.site_id}
                  name={site.site_name}
                  reason={site.reason}
                  rank={plan.assignments.length + index + 1}
                  site={siteById.get(site.site_id)}
                  maximumValue={maxValue}
                />
              ))}
            </div>
          </div>
        </Panel>

        <div className={styles.sideColumn}>
          <Panel
            title="⚙️ Constraints"
            hint={bindingConstraints.length ? 'binding constraints' : 'capacity available'}
          >
            <div className={styles.constraintList}>
              <ConstraintBar
                label="Boats available today"
                value={availableBoats}
                maximum={scenario.boats.length}
                display={`${availableBoats} / ${scenario.boats.length}`}
              />
              <ConstraintBar
                label="Dive-team hours"
                value={totalHours}
                maximum={totalTeamHours}
                display={`${totalHours.toFixed(1)} / ${totalTeamHours.toFixed(1)} h`}
              />
              <ConstraintBar
                label="Budget cap"
                value={totalCost}
                maximum={scenario.budget_usd}
                display={`${currency(totalCost)} / ${currency(scenario.budget_usd)}`}
              />
              <ConstraintBar
                label="Daylight window"
                value={totalHours}
                maximum={scenario.daylight_hours}
                display={`${totalHours.toFixed(1)} / ${scenario.daylight_hours} h`}
              />
            </div>
            {bindingConstraints.length > 0 ? (
              <div className={styles.bindingList}>
                {bindingConstraints.map((constraint) => (
                  <span key={constraint}>{constraint.replace(/_/g, ' ')}</span>
                ))}
              </div>
            ) : null}
          </Panel>

          <Panel title="📊 Allocation by action class">
            {actionCosts.length === 0 ? (
              <p className={styles.muted}>No assignments in the current plan.</p>
            ) : (
              <div className={styles.categoryList}>
                {actionCosts.map((item) => (
                  <div className={styles.categoryRow} key={item.label}>
                    <span>{item.label}</span>
                    <span>
                      {allocationTotal > 0 ? Math.round((item.value / allocationTotal) * 100) : 0}%
                    </span>
                    <span className={styles.categoryTrack}>
                      <span style={{ width: progress(item.value, allocationTotal) }} />
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
