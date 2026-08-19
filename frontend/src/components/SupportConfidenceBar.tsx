import { cx } from '@/lib/cx';
import type { Cause } from '@/types';

import styles from './SupportConfidenceBar.module.css';

/**
 * A compact card for one cause. The visible metric is confidence; the backend
 * support score drives the status label and colour without adding a second bar.
 *
 * Deliberate constraints, from `.agents/teammates/frontend.md`:
 *
 * - The word is "support", never "probability" or "likelihood". These scores
 *   are not calibrated against expert-labeled cases, so calling them
 *   probabilities would overstate what they prove.
 * - Confidence is scaled against a full 0 to 1 track of its own.
 * - Support remains a required input because it determines the status, but it
 *   is intentionally not rendered as a second visual line in this compact UI.
 *
 * Rendering four of these side by side is the approved layout. Feeding them
 * into a pie or a stacked bar is not.
 */

const CAUSE_LABELS: Record<Cause, string> = {
  thermal: 'Thermal stress',
  disease: 'Disease',
  runoff: 'Runoff',
  physical: 'Physical damage',
};

const CAUSE_ICONS: Record<Cause, string> = {
  thermal: '🌡️',
  disease: '🦠',
  runoff: '🌧️',
  physical: '⚓',
};

function toPercent(value: number): string {
  return `${Math.round(Math.min(Math.max(value, 0), 1) * 100)}%`;
}

type EvidenceStatus = 'supported' | 'investigating' | 'unsupported';

const STATUS_LABELS: Record<EvidenceStatus, string> = {
  supported: 'Supported',
  investigating: 'Investigating',
  unsupported: 'Unsupported',
};

function statusForEvidence(support: number, isDominant: boolean): EvidenceStatus {
  if (isDominant || support >= 0.75) return 'supported';
  if (support >= 0.2) return 'investigating';
  return 'unsupported';
}

export interface SupportConfidenceBarProps {
  cause: Cause;
  /** Support score on 0 to 1. Not a probability. */
  support: number;
  /** Confidence in that support score, on 0 to 1. */
  confidence: number;
  /** True when this cause is currently in play for the site. */
  isDominant?: boolean;
  /** One backend-validated sentence for the card. */
  displaySummary: string;
  /** One to three backend-validated evidence points. */
  keyFindings: string[];
}

export function SupportConfidenceBar({
  cause,
  support,
  confidence,
  isDominant = false,
  displaySummary,
  keyFindings,
}: SupportConfidenceBarProps) {
  const label = CAUSE_LABELS[cause];
  const status = statusForEvidence(support, isDominant);

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.icon} aria-hidden="true">
          {CAUSE_ICONS[cause]}
        </span>
        <span className={styles.label}>{label}</span>
        <span className={cx(styles.status, styles[`status-${status}`])}>
          <span className={styles.statusDot} aria-hidden="true" />
          {STATUS_LABELS[status]}
        </span>
      </div>

      <div className={styles.metric}>
        <span className={styles.metricLabel}>Confidence</span>
        <span className={styles.metricValue}>{toPercent(confidence)}</span>
        <div
          className={cx(styles.track, styles.trackConfidence, styles[`track-${status}`])}
          role="meter"
          aria-valuenow={confidence}
          aria-valuemin={0}
          aria-valuemax={1}
          aria-label={`${label} confidence, ${toPercent(confidence)}`}
        >
          <div
            className={cx(styles.fill, styles.fillConfidence, styles[`fill-${status}`])}
            style={{ width: toPercent(confidence) }}
          />
        </div>
      </div>

      <p className={styles.summary}>{displaySummary}</p>
      <ul className={styles.findings}>
        {keyFindings.map((finding, index) => (
          <li key={`${cause}-finding-${index}`}>{finding}</li>
        ))}
      </ul>
    </div>
  );
}
