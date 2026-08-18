import type { ReactNode } from 'react';

import styles from './StatTile.module.css';

/**
 * A single headline figure.
 *
 * The reference styles this note in red or green to signal a rising or falling
 * trend. That is not carried over: this dashboard has no comparable previous
 * period, and colouring a number as good or bad would assert a judgement the
 * data does not support. The note is neutral, and says what the figure is
 * scoped to instead.
 */

export interface StatTileProps {
  label: ReactNode;
  value: ReactNode;
  /** Small trailing unit, rendered quieter than the value. */
  unit?: ReactNode;
  /** What the figure is scoped to. */
  note?: ReactNode;
  /** Large watermark glyph. Decorative only. */
  decoration?: string;
}

export function StatTile({ label, value, unit, note, decoration }: StatTileProps) {
  return (
    <div className={styles.root}>
      <div className={styles.label}>{label}</div>
      <div className={styles.value}>
        {value}
        {unit !== undefined ? <span className={styles.unit}> {unit}</span> : null}
      </div>
      {note !== undefined ? <div className={styles.note}>{note}</div> : null}
      {decoration !== undefined ? (
        <span className={styles.deco} aria-hidden="true">
          {decoration}
        </span>
      ) : null}
    </div>
  );
}
