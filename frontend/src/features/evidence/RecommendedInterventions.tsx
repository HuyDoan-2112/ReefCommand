'use client';

import { Panel } from '@/components';
import { useCurrentPlan } from '@/hooks/usePlan';
import { useSiteTrace } from '@/hooks/useTrace';

import {
  evidenceRequestLabel,
  readCoordinatorDecision,
  readEligibleActions,
} from './coordinatorDecision';
import styles from './RecommendedInterventions.module.css';

export function RecommendedInterventions({ siteId }: { siteId: string }) {
  const { data: plan } = useCurrentPlan();
  const { data: trace, isPending, error } = useSiteTrace(plan?.plan_id ?? null, siteId);

  if (isPending) {
    return (
      <Panel title="Recommended interventions">
        <p className={styles.muted}>Loading policy-approved actions...</p>
      </Panel>
    );
  }

  if (error || !trace) {
    return (
      <Panel title="Recommended interventions">
        <p className={styles.muted}>No validated recommendation is available for this plan.</p>
      </Panel>
    );
  }

  const decision = readCoordinatorDecision(trace);
  const eligibleById = new Map(
    readEligibleActions(trace).map((action) => [action.action_id, action] as const),
  );

  return (
    <Panel
      title="Recommended interventions"
      hint={decision?.executor === 'llm' ? 'live Coordinator output' : 'offline fixture baseline'}
    >
      {!decision ? (
        <p className={styles.muted}>The Coordinator did not return a usable validated decision.</p>
      ) : decision.approved_actions.length > 0 ? (
        <ol className={styles.list}>
          {decision.approved_actions.map((action, index) => {
            const eligible = eligibleById.get(action.action_id);
            return (
              <li key={action.action_id} className={styles.item}>
                <span className={styles.number}>{index + 1}</span>
                <div className={styles.body}>
                  <div className={styles.titleRow}>
                    <strong>{action.action_id.replace(/_/g, ' ')}</strong>
                    <span>{action.priority}</span>
                  </div>
                  <p>{action.rationale}</p>
                  {eligible?.provenance ? (
                    <div className={styles.source} title={eligible.provenance}>
                      {eligible.provenance}
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className={styles.hold}>
          <strong>No intervention approved yet</strong>
          <p>{decision.reasoning_summary}</p>
          {decision.next_evidence.length > 0 ? (
            <ul>
              {[...decision.next_evidence]
                .sort((a, b) => a.priority - b.priority)
                .map((request) => (
                  <li key={`${request.type}-${request.priority}`}>
                    {evidenceRequestLabel(request.type)}: {request.rationale}
                  </li>
                ))}
            </ul>
          ) : null}
        </div>
      )}

      <div className={styles.notice}>
        Recommendations come only from the source-grounded knowledge base and always require manager
        approval. The Coordinator cannot invent an intervention.
      </div>
    </Panel>
  );
}
