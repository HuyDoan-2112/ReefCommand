'use client';

import Link from 'next/link';
import { useLayoutEffect, useRef } from 'react';

import { Panel, ProvenanceBadge, SimulatedDataBanner, StatTile } from '@/components';
import { useCurrentPlan } from '@/hooks/usePlan';
import { useSiteEvidenceBatch, useSites } from '@/hooks/useSites';
import { cx } from '@/lib/cx';
import type {
  Assignment,
  DeferredSite,
  FusedEvidence,
  Priority,
  ResponsePlan,
  SiteView,
} from '@/types';

import { SiteMap } from './SiteMap';

import styles from './CurrentPlan.module.css';

/**
 * The current response plan, rendered as an operations plan rather than an
 * AI answer.
 *
 * Every explanation on screen is a field on the API, not text composed here:
 * `evidence_summary`, `remaining_uncertainty`, `compatibility_rationale` and
 * each deferral's `reason`. That is deliberate, per docs/api_requirements.md.
 * The frontend cannot accidentally omit one, and the backend cannot quietly
 * stop producing one.
 */

const PRIORITY_LABEL: Record<Priority, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

const PRIORITY_COLOR: Record<Priority, string> = {
  high: 'var(--priority-high)',
  medium: 'var(--priority-medium)',
  low: 'var(--priority-low)',
};

/**
 * Turn an optimizer constraint key into something a manager reads.
 *
 * The backend currently emits raw keys such as "dive_team_hours". Mapping them
 * here is a stopgap: docs/api_requirements.md says the backend should send
 * plain-language trade-off text, and it does not yet. An unmapped key falls
 * back to the key itself rather than being hidden, so a new constraint is
 * visible rather than silently dropped.
 */
const CONSTRAINT_LABEL: Record<string, string> = {
  boat_count: 'every boat is committed',
  boat_hours: 'boat hours are exhausted',
  dive_team_count: 'every dive team is committed',
  dive_team_hours: 'dive team hours are exhausted',
  shade_units: 'no shade units left',
  monitoring_kits: 'no monitoring kits left',
  sampling_kits: 'no sampling kits left',
  budget_usd: 'the budget is spent',
  daylight_hours: 'daylight is used up',
};

function constraintLabel(key: string): string {
  return CONSTRAINT_LABEL[key] ?? key;
}

function currency(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });
}

function AssignmentRow({ assignment, rank }: { assignment: Assignment; rank: number }) {
  return (
    <>
      <div className={styles.row}>
        <span className={styles.rank}>{rank}</span>

        <span className={styles.siteCell}>
          {assignment.site_name}
          <span className={styles.siteMeta}>{assignment.action_id.replace(/_/g, ' ')}</span>
        </span>

        <span className={styles.crew}>
          {(assignment.boat_id ?? assignment.team_id) ? (
            <>
              <span>
                {assignment.boat_id
                  ? `Boat ${assignment.boat_id.replace(/^boat_/, '').toUpperCase()}`
                  : 'No boat'}
              </span>
              <span>
                {assignment.team_id
                  ? `Dive team ${assignment.team_id.replace(/^team_/, '').toUpperCase()}`
                  : 'No dive team'}
              </span>
            </>
          ) : (
            <span className={styles.crewMissing}>No crew assigned</span>
          )}
        </span>

        <span style={{ color: PRIORITY_COLOR[assignment.priority], fontWeight: 700 }}>
          {PRIORITY_LABEL[assignment.priority]}
        </span>

        <span className={styles.numeric}>{assignment.estimated_hours.toFixed(1)} h</span>
        <span className={styles.numeric}>{currency(assignment.estimated_cost_usd)}</span>
      </div>

      <div className={styles.row} style={{ borderBottom: 'none', paddingTop: 0 }}>
        <span />
        <div className={styles.why}>
          <div>
            <span className={styles.whyLabel}>Evidence: </span>
            {assignment.evidence_summary}
          </div>
          <div>
            <span className={styles.whyLabel}>Still uncertain: </span>
            {assignment.remaining_uncertainty}
          </div>
          <details className={styles.source}>
            <summary className={styles.sourceSummary}>
              Why this action is eligible, with its cited source
            </summary>
            <div className={styles.sourceBody}>{assignment.compatibility_rationale}</div>
          </details>
          {assignment.requires_manager_approval ? (
            <div>
              <span className={styles.approval}>Requires manager approval</span>
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}

function DeferredRow({ site }: { site: DeferredSite }) {
  return (
    <div className={styles.deferredItem}>
      <span aria-hidden="true">⏸️</span>
      <div className={styles.deferredBody}>
        <div className={styles.deferredName}>{site.site_name}</div>
        <div className={styles.deferredReason}>{site.reason}</div>
      </div>
      {site.fallback_action_id ? (
        <span className={styles.approval}>
          Fallback: {site.fallback_action_id.replace(/_/g, ' ')}
        </span>
      ) : null}
    </div>
  );
}

const STUDY_AREA_LABEL = 'Florida Keys';

function reportCount(evidence: FusedEvidence | undefined): number {
  if (!evidence) return 0;
  const references = Object.values(evidence.by_cause).flatMap((cause) =>
    (cause?.citations ?? [])
      .filter((citation) => citation.source.toLowerCase().includes('structured form'))
      .map((citation) => citation.reference ?? citation.source),
  );
  return new Set(references).size;
}

function thermalSummary(evidence: FusedEvidence | undefined): string {
  return evidence?.by_cause.thermal?.display_summary ?? 'Thermal evidence is loading';
}

function causeSummary(
  assignment: Assignment | null,
  site: SiteView | undefined,
  evidence: FusedEvidence | undefined,
): string {
  if (assignment) return assignment.evidence_summary;
  const causes = site?.dominant_causes ?? [];
  const summaries = causes
    .map((cause) => evidence?.by_cause[cause]?.display_summary)
    .filter((summary): summary is string => Boolean(summary));
  return summaries.length > 0 ? summaries.join(' ') : 'No dominant cause is currently supported.';
}

function statusLabel(priority: Priority | null): string {
  if (priority === 'high') return 'Critical';
  if (priority === 'medium') return 'Serious';
  return 'Watch';
}

function PriorityQueue({ plan }: { plan: ResponsePlan }) {
  const deferred = plan.deferred ?? [];
  const { data: sites } = useSites();
  const siteIds = sites?.map((site) => site.site_id) ?? [];
  const evidenceQueries = useSiteEvidenceBatch(siteIds);
  const sitesById = new Map((sites ?? []).map((site) => [site.site_id, site]));
  const evidenceBySite = new Map(
    siteIds.map((siteId, index) => [siteId, evidenceQueries[index]?.data] as const),
  );

  function renderCardMeta(siteId: string) {
    const evidence = evidenceBySite.get(siteId);
    const count = reportCount(evidence);
    return `${thermalSummary(evidence)} · ${count} synthetic report${count === 1 ? '' : 's'} · ${STUDY_AREA_LABEL}`;
  }

  return (
    <Panel
      title="Priority queue"
      hint="current plan order"
      className={styles.queuePanel}
      bodyClassName={styles.queuePanelBody}
    >
      <div className={styles.queueList}>
        {plan.assignments.map((assignment, index) => (
          <Link
            href={`/sites/${assignment.site_id}`}
            className={styles.queueCard}
            key={`${assignment.site_id}-${assignment.action_id}`}
          >
            <span className={styles.queueRank}>{index + 1}</span>
            <span className={styles.queueBody}>
              <span className={styles.queueHead}>
                <strong>{assignment.site_name}</strong>
                <span
                  className={styles.queuePriority}
                  style={{ color: PRIORITY_COLOR[assignment.priority] }}
                >
                  {statusLabel(assignment.priority)}
                </span>
              </span>
              <span className={styles.queueMeta}>{renderCardMeta(assignment.site_id)}</span>
              <span className={styles.queueAction}>{assignment.action_id.replace(/_/g, ' ')}</span>
              <span className={styles.queueReason}>
                Coordinator:{' '}
                {causeSummary(
                  assignment,
                  sitesById.get(assignment.site_id),
                  evidenceBySite.get(assignment.site_id),
                )}
              </span>
              {assignment.requires_manager_approval ? (
                <span className={styles.queueApproval}>Manager approval required</span>
              ) : null}
            </span>
          </Link>
        ))}

        {deferred.map((site) => (
          <Link
            href={`/sites/${site.site_id}`}
            className={styles.queueCardMuted}
            key={site.site_id}
          >
            <span className={styles.queuePause} aria-hidden="true">
              ⏸
            </span>
            <span className={styles.queueBody}>
              <span className={styles.queueHead}>
                <strong>{site.site_name}</strong>
                <span className={styles.queueDeferred}>{statusLabel(null)}</span>
              </span>
              <span className={styles.queueMeta}>{renderCardMeta(site.site_id)}</span>
              <span className={styles.queueAction}>
                {site.fallback_action_id
                  ? site.fallback_action_id.replace(/_/g, ' ')
                  : 'monitoring'}
              </span>
              <span className={styles.queueReason}>
                Coordinator:{' '}
                {causeSummary(null, sitesById.get(site.site_id), evidenceBySite.get(site.site_id))}
              </span>
              <span className={styles.queueReason}>{site.reason}</span>
            </span>
          </Link>
        ))}
      </div>
    </Panel>
  );
}

function PlanBody({ plan, surface }: { plan: ResponsePlan; surface: 'command' | 'optimizer' }) {
  const commandGridRef = useRef<HTMLDivElement>(null);
  const totalHours = plan.assignments.reduce((sum, a) => sum + a.estimated_hours, 0);
  const totalCost = plan.assignments.reduce((sum, a) => sum + a.estimated_cost_usd, 0);
  const binding = plan.binding_constraints ?? [];
  const deferred = plan.deferred ?? [];

  useLayoutEffect(() => {
    if (surface !== 'command') return;

    const grid = commandGridRef.current;
    if (!grid) return;

    const syncRowHeight = () => {
      if (window.matchMedia('(max-width: 1180px)').matches) {
        grid.style.removeProperty('--command-row-height');
        return;
      }

      const mapSvg = grid.querySelector('svg');
      const mapHeight = mapSvg?.getBoundingClientRect().height ?? 0;
      if (mapHeight > 0) {
        grid.style.setProperty('--command-row-height', `${mapHeight}px`);
      }
    };

    const observer = new ResizeObserver(syncRowHeight);
    observer.observe(grid);
    const mutationObserver = new MutationObserver(syncRowHeight);
    mutationObserver.observe(grid, { childList: true, subtree: true });
    syncRowHeight();

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, [surface]);

  return (
    <div className={styles.root}>
      {surface === 'command' ? (
        <>
          <SimulatedDataBanner
            text={plan.scenario_banner}
            detail={`Scenario ${plan.scenario_id}. Plan generated ${new Date(plan.generated_at).toLocaleString()}.`}
          />

          <div className={styles.statRow}>
            <StatTile
              label="🛥️ Sites tasked"
              value={plan.assignments.length}
              unit={`/ ${plan.assignments.length + deferred.length}`}
              note="the rest are deferred"
              decoration="🛥️"
            />
            <StatTile
              label="🎯 Strategic value"
              value={plan.total_strategic_value.toFixed(2)}
              note="prototype objective achieved"
              decoration="🎯"
            />
            <StatTile
              label="⏱️ Dive hours"
              value={totalHours.toFixed(1)}
              note="committed across the plan"
              decoration="⏱️"
            />
            <StatTile
              label="💵 Cost"
              value={currency(totalCost)}
              note={<ProvenanceBadge provenance="simulated" />}
              decoration="💵"
            />
          </div>

          <div ref={commandGridRef} className={styles.commandGrid}>
            <div className={styles.mapPanel}>
              <SiteMap />
            </div>
            <PriorityQueue plan={plan} />
          </div>
        </>
      ) : null}

      {surface === 'optimizer' ? (
        <>
          <Panel
            title="Assignments"
            hint={`${plan.assignments.length} tasked, each requiring manager approval`}
            scrollX
          >
            {plan.assignments.length === 0 ? (
              <p className={styles.empty}>
                No site could be tasked with the capacity in this scenario. Every site appears under
                deferrals below with the reason.
              </p>
            ) : (
              <>
                <div className={cx(styles.row, styles.rowHead)}>
                  <span />
                  <span>Site and action</span>
                  <span>Crew</span>
                  <span>Priority</span>
                  <span>Hours</span>
                  <span>Cost</span>
                </div>
                {plan.assignments.map((assignment, index) => (
                  <AssignmentRow
                    key={`${assignment.site_id}-${assignment.action_id}`}
                    assignment={assignment}
                    rank={index + 1}
                  />
                ))}
              </>
            )}
          </Panel>

          <Panel
            title="Why these trade-offs"
            hint={binding.length > 0 ? 'binding constraints' : 'nothing was binding'}
          >
            {binding.length > 0 ? (
              <>
                <div className={styles.constraintList}>
                  {binding.map((key) => (
                    <span key={key} className={styles.constraint}>
                      <span aria-hidden="true">⛔</span>
                      {constraintLabel(key)}
                    </span>
                  ))}
                </div>
                <p className={styles.empty} style={{ paddingBottom: 0 }}>
                  These are the limits that stopped the optimizer from tasking more sites. Relaxing
                  any one of them is what would change the plan.
                </p>
              </>
            ) : (
              <p className={styles.empty}>
                No capacity limit was binding. The plan is shaped by which actions were
                policy-eligible, not by what the fleet could reach.
              </p>
            )}
          </Panel>

          <Panel title="Deferred" hint={`${deferred.length} site(s) not tasked this cycle`}>
            {deferred.length === 0 ? (
              <p className={styles.empty}>Every site with an eligible action was tasked.</p>
            ) : (
              <div className={styles.deferred}>
                {deferred.map((site) => (
                  <DeferredRow key={site.site_id} site={site} />
                ))}
              </div>
            )}
          </Panel>
        </>
      ) : null}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className={styles.root}>
      <Panel title="Assignments" hint="loading">
        {[0, 1, 2].map((row) => (
          <div key={row} className={styles.skeletonRow}>
            {[0, 1, 2, 3, 4, 5].map((cell) => (
              <div key={cell} className={styles.skeleton} />
            ))}
          </div>
        ))}
      </Panel>
    </div>
  );
}

export function CurrentPlan({ surface = 'command' }: { surface?: 'command' | 'optimizer' }) {
  const { data: plan, isPending, error } = useCurrentPlan();

  if (isPending) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div className={styles.error}>
        <strong>Could not load the current plan.</strong>
        <div style={{ marginTop: 4 }}>{error.message}</div>
        <div style={{ marginTop: 6 }}>
          Check that the backend is running and that <code>/api</code> reaches it.
        </div>
      </div>
    );
  }

  return <PlanBody plan={plan} surface={surface} />;
}
