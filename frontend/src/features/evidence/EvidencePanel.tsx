'use client';

import { SupportConfidenceBar } from '@/components';
import { useSiteEvidence } from '@/hooks/useSites';
import { CAUSES, type CauseEvidence } from '@/types';

import styles from './EvidencePanel.module.css';

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

  const visibleCitations = citations.slice(0, 2);
  const hiddenCount = citations.length - visibleCitations.length;

  return (
    <ul className={styles.citationList}>
      {visibleCitations.map((citation, index) => (
        <li key={`${citation.source}-${index}`} className={styles.citation}>
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
      {hiddenCount > 0 ? (
        <li className={styles.moreSources}>+{hiddenCount} more sources in the audit trace</li>
      ) : null}
    </ul>
  );
}

export function EvidencePanel({ siteId, planId }: { siteId: string; planId: string | null }) {
  const { data: evidence, isPending, error } = useSiteEvidence(siteId, planId);

  if (isPending) {
    return <p className={styles.muted}>Loading the four hypothesis assessments...</p>;
  }

  if (error) {
    return <p className={styles.muted}>No fused evidence for this site yet. {error.message}</p>;
  }

  const dominant = new Set(evidence.dominant_causes ?? []);

  return (
    <section className={styles.root}>
      <div className={styles.sectionHead}>
        <h3>Hypothesis investigation - 4 independent modules</h3>
        <span>Confidence bars are status-coloured; support remains in the audit trace</span>
      </div>
      <div className={styles.causeGrid}>
        {CAUSES.map((cause) => {
          const entry = evidence.by_cause[cause];
          if (!entry) return null;
          return (
            <article key={cause} className={styles.causeCard}>
              <SupportConfidenceBar
                cause={cause}
                support={entry.support}
                confidence={entry.confidence}
                isDominant={dominant.has(cause)}
                displaySummary={entry.display_summary}
                keyFindings={entry.key_findings}
              />
              <Citations evidence={entry} />
            </article>
          );
        })}
      </div>
      <p className={styles.disclaimer}>
        Status is based on the backend support score. Confidence is not a probability.
      </p>
    </section>
  );
}
