import { cx } from '@/lib/cx';

import styles from './ConditionBadge.module.css';

/**
 * How serious a site's situation is.
 *
 * `basis` is required, not optional, on purpose. The reference shows a bare
 * "Critical" chip driven by a single thermal number. This system maintains four
 * competing causes, so a bare severity label would quietly assert that one
 * reading summarises a site. Requiring the caller to state what the rating is
 * derived from means the label always travels with its own scope.
 *
 * Severity is carried by a word as well as a colour, so it survives without hue.
 */

export type Condition = 'good' | 'warning' | 'serious' | 'critical';

const LABELS: Record<Condition, string> = {
  good: 'Healthy',
  warning: 'Watch',
  serious: 'Serious',
  critical: 'Critical',
};

const VARIANTS: Record<Condition, string | undefined> = {
  good: styles.good,
  warning: styles.warning,
  serious: styles.serious,
  critical: styles.critical,
};

export interface ConditionBadgeProps {
  condition: Condition;
  /**
   * What this rating is derived from, for example
   * "thermal evidence only, before fusion".
   */
  basis: string;
  /** Override the visible word. The basis is still announced. */
  label?: string;
}

export function ConditionBadge({ condition, basis, label }: ConditionBadgeProps) {
  return (
    <span className={cx(styles.root, VARIANTS[condition])} title={`Based on ${basis}`}>
      <span className={styles.swatch} aria-hidden="true" />
      {label ?? LABELS[condition]}
      <span className="visually-hidden">, based on {basis}</span>
    </span>
  );
}
