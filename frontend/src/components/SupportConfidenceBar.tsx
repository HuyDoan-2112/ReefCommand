import { cx } from '@/lib/cx';
import type { Cause } from '@/types';

import styles from './SupportConfidenceBar.module.css';

/**
 * The support score for one cause, with the confidence in that score beneath it.
 *
 * Deliberate constraints, from `.agents/teammates/frontend.md`:
 *
 * - The word is "support", never "probability" or "likelihood". These scores
 *   are not calibrated against expert-labeled cases, so calling them
 *   probabilities would overstate what they prove.
 * - Confidence is always rendered next to support. A component cannot render
 *   one without the other, because both props are required.
 * - Each bar is scaled against a full 0 to 1 track of its own. The four causes
 *   are not competing shares of one quantity, so nothing here is ever scaled
 *   relative to the other causes.
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

function format(value: number): string {
  return value.toFixed(2);
}

export interface SupportConfidenceBarProps {
  cause: Cause;
  /** Support score on 0 to 1. Not a probability. */
  support: number;
  /** Confidence in that support score, on 0 to 1. */
  confidence: number;
  /** True when this cause is currently in play for the site. */
  isDominant?: boolean;
  /** The investigator's short explanation, shown beneath the bars. */
  rationale?: string;
}

export function SupportConfidenceBar({
  cause,
  support,
  confidence,
  isDominant = false,
  rationale,
}: SupportConfidenceBarProps) {
  const label = CAUSE_LABELS[cause];

  return (
    <div className={styles.root}>
      <div className={styles.header}>
        <span className={styles.icon} aria-hidden="true">
          {CAUSE_ICONS[cause]}
        </span>
        <span className={styles.label}>{label}</span>
        {isDominant ? <span className={styles.dominant}>In play</span> : null}
      </div>

      <div className={styles.metric}>
        <span className={styles.metricLabel}>Support</span>
        <span className={styles.metricValue}>{format(support)}</span>
        <div
          className={styles.track}
          role="meter"
          aria-valuenow={support}
          aria-valuemin={0}
          aria-valuemax={1}
          aria-label={`${label} support score, ${format(support)} out of 1`}
        >
          <div
            className={cx(styles.fill, styles.fillSupport)}
            style={{ width: toPercent(support) }}
          />
        </div>
      </div>

      <div className={styles.metric}>
        <span className={styles.metricLabel}>Confidence</span>
        <span className={styles.metricValue}>{format(confidence)}</span>
        <div
          className={cx(styles.track, styles.trackConfidence)}
          role="meter"
          aria-valuenow={confidence}
          aria-valuemin={0}
          aria-valuemax={1}
          aria-label={`Confidence in the ${label} support score, ${format(confidence)} out of 1`}
        >
          <div
            className={cx(styles.fill, styles.fillConfidence)}
            style={{ width: toPercent(confidence) }}
          />
        </div>
      </div>

      {rationale ? <p className={styles.rationale}>{rationale}</p> : null}
    </div>
  );
}
