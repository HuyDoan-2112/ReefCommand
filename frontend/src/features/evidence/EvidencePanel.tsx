'use client';

import { Panel, ProvenanceBadge, SupportConfidenceBar } from '@/components';
import { useCurrentPlan } from '@/hooks/usePlan';
import { useSiteEvidence } from '@/hooks/useSites';
import { useSiteTrace } from '@/hooks/useTrace';
import { CAUSES, type CauseEvidence } from '@/types';

import styles from './EvidencePanel.module.css';
import { evidenceRequestLabel, readCoordinatorDecision } from './coordinatorDecision';

/**
 * The four competing causes for one site, and what the Coordinator decided.
 *
 * The four support scores are rendered as four independent bars, each against
 * its own full 0 to 1 track. They are not normalized, they do not sum to 1, and
 * more than one cause can be in play at once. That is the whole point of the
 * four-cause model, so nothing here draws them as parts of a whole.
 *
 * Ambiguity is shown next to them because it is the number that explains why
 * the Coordinator sometimes asks for another observation instead of acting: two
 * causes close together imply different responses.
 */

function Citations({ evidence }: { evidence: CauseEvidence }) {
  const citations = evidence.citations ?? [];
  if (citations.length === 0) {
    return <p className={styles.noCitations}>No citation was attached to this assessment.</p>;
  }

  return (
    <ul className={styles.citationList}>
      {citations.map((citation, index) => (
        <li key={`${citation.source}-${index}`} className={styles.citation}>
          <ProvenanceBadge provenance={citation.provenance} />
          <span className={styles.citationBody}>
            <span className={styles.citationSource}>{citation.source}</span>
            {citation.reference ? (
              <span className={styles.citationRef}>{citation.reference}</span>
            ) : null}
            {citation.review_status ? (
              <span className={styles.citationMeta}>Review status: {citation.review_status}</span>
            ) : null}
            {citation.reporting_organization ? (
              <span className={styles.citationMeta}>{citation.reporting_organization}</span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function EvidencePanel({ siteId }: { siteId: string }) {
  const { data: evidence, isPending, error } = useSiteEvidence(siteId);
  const { data: plan } = useCurrentPlan();
  const { data: trace } = useSiteTrace(plan?.plan_id ?? null, siteId);

  if (isPending) {
    return (
      <Panel title="Evidence">
        <p className={styles.muted}>Loading evidence...</p>
      </Panel>
    );
  }

  if (error) {
    return (
      <Panel title="Evidence">
        <p className={styles.muted}>No fused evidence for this site yet. {error.message}</p>
      </Panel>
    );
  }

  const decision = readCoordinatorDecision(trace);
  const dominant = new Set(evidence.dominant_causes ?? []);
  const total = CAUSES.reduce((sum, cause) => sum + (evidence.by_cause[cause]?.support ?? 0), 0);

  return (
    <div className={styles.root}>
      <Panel
        title="Evidence for each cause"
        hint={`four independent scores, summing to ${total.toFixed(2)}`}
      >
        <div className={styles.causeGrid}>
          {CAUSES.map((cause) => {
            const entry = evidence.by_cause[cause];
            if (!entry) return null;
            return (
              <div key={cause} className={styles.causeCard}>
                <SupportConfidenceBar
                  cause={cause}
                  support={entry.support}
                  confidence={entry.confidence}
                  isDominant={dominant.has(cause)}
                  rationale={entry.rationale}
                />
              </div>
            );
          })}
        </div>

        <div className={styles.readouts}>
          <div className={styles.readout}>
            <span className={styles.readoutLabel}>Ambiguity</span>
            <span className={styles.readoutValue}>{evidence.ambiguity.toFixed(2)}</span>
            <span className={styles.readoutNote}>
              How close the leading causes are. High ambiguity is when two causes imply different
              responses, which is what the Coordinator resolves by asking for more evidence.
            </span>
          </div>
          <div className={styles.readout}>
            <span className={styles.readoutLabel}>Lowest confidence</span>
            <span className={styles.readoutValue}>{evidence.lowest_confidence.toFixed(2)}</span>
            <span className={styles.readoutNote}>
              The weakest of the four assessments. A high support score resting on low confidence is
              not the same finding as one resting on high confidence.
            </span>
          </div>
        </div>

        <p className={styles.disclaimer}>
          These are support scores, not probabilities. They are not normalized against each other
          and the four causes are not assumed independent, so more than one can be well supported at
          once.
        </p>
      </Panel>

      <Panel
        title="What the Coordinator decided"
        hint={
          decision
            ? decision.executor === 'llm'
              ? `${decision.provider ?? 'model'} ${decision.model ?? ''}`.trim()
              : 'offline fixture, no model call'
            : undefined
        }
      >
        {!decision ? (
          <p className={styles.muted}>
            No Coordinator decision is available for this site in the current plan&apos;s trace.
          </p>
        ) : (
          <>
            <div
              className={
                decision.additional_evidence_needed ? styles.verdictAsking : styles.verdictActing
              }
            >
              <span className={styles.verdictIcon} aria-hidden="true">
                {decision.additional_evidence_needed ? '🔍' : '✅'}
              </span>
              <div>
                <div className={styles.verdictTitle}>
                  {decision.additional_evidence_needed
                    ? 'Holding for more evidence'
                    : 'Evidence judged sufficient to act'}
                </div>
                <p className={styles.verdictBody}>{decision.reasoning_summary}</p>
              </div>
            </div>

            {decision.next_evidence.length > 0 ? (
              <div className={styles.requests}>
                <div className={styles.requestsTitle}>Requested before acting</div>
                {[...decision.next_evidence]
                  .sort((a, b) => a.priority - b.priority)
                  .map((request) => (
                    <div key={`${request.type}-${request.priority}`} className={styles.request}>
                      <span className={styles.requestPriority}>{request.priority}</span>
                      <div>
                        <div className={styles.requestType}>
                          {evidenceRequestLabel(request.type)}
                        </div>
                        <div className={styles.requestWhy}>{request.rationale}</div>
                      </div>
                    </div>
                  ))}
              </div>
            ) : null}

            {decision.approved_actions.length > 0 ? (
              <div className={styles.approved}>
                <div className={styles.requestsTitle}>
                  Approved as worth acting on, subject to capacity
                </div>
                {decision.approved_actions.map((action) => (
                  <div key={action.action_id} className={styles.approvedItem}>
                    <span className={styles.approvedName}>
                      {action.action_id.replace(/_/g, ' ')}
                    </span>
                    <span className={styles.approvedPriority}>{action.priority}</span>
                    <span className={styles.approvedWhy}>{action.rationale}</span>
                  </div>
                ))}
                <p className={styles.disclaimer}>
                  The Coordinator chooses among actions the policy engine already found eligible. It
                  cannot invent one, and it does not assign boats or teams.
                </p>
              </div>
            ) : null}
          </>
        )}
      </Panel>

      <Panel title="Citations" hint="every score carries its sources">
        <div className={styles.citationGroups}>
          {CAUSES.map((cause) => {
            const entry = evidence.by_cause[cause];
            if (!entry) return null;
            return (
              <div key={cause} className={styles.citationGroup}>
                <div className={styles.citationGroupTitle}>{cause}</div>
                <Citations evidence={entry} />
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
