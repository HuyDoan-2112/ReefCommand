import type { ReactNode } from 'react';

import { cx } from '@/lib/cx';

import styles from './Panel.module.css';

/**
 * The standard card container.
 *
 * `hint` is the small right-aligned note in the header. It is where a surface
 * says what a number is scoped to, which keeps a caveat next to its figure
 * rather than in a legend somewhere else.
 */

export interface PanelProps {
  title?: ReactNode;
  hint?: ReactNode;
  /** Rendered in the header, between the title and the hint. */
  actions?: ReactNode;
  /** Let wide content scroll inside the panel instead of the page. */
  scrollX?: boolean;
  className?: string;
  children: ReactNode;
}

export function Panel({ title, hint, actions, scrollX = false, className, children }: PanelProps) {
  return (
    <section className={cx(styles.root, className)}>
      {title !== undefined || actions !== undefined || hint !== undefined ? (
        <header className={styles.head}>
          {title !== undefined ? <h3 className={styles.title}>{title}</h3> : null}
          {actions}
          {hint !== undefined ? <span className={styles.hint}>{hint}</span> : null}
        </header>
      ) : null}
      <div className={cx(styles.body, scrollX && styles.scroll)}>{children}</div>
    </section>
  );
}
