import { cx } from '@/lib/cx';
import type { Provenance } from '@/types';

import styles from './ProvenanceBadge.module.css';

/**
 * Labels where a value came from.
 *
 * `AGENTS.md` requires that simulated and synthetic data are never presented as
 * real, and `.agents/teammates/frontend.md` requires the four kinds be
 * distinguishable for a reader who is not colorblind-typical.
 *
 * So each kind carries three independent cues: a distinct glyph, its own word,
 * and a colour. The two kinds that must never be mistaken for measurements,
 * simulated and synthetic, additionally take a dashed border. Remove the colour
 * entirely and the badge still reads correctly.
 */

const LABELS: Record<Provenance, string> = {
  live: 'Live',
  cache: 'Cached',
  simulated: 'Simulated',
  synthetic: 'Synthetic',
};

const GLYPHS: Partial<Record<Provenance, string>> = {
  live: '●',
  cache: '■',
  simulated: '▲',
};

const DESCRIPTIONS: Record<Provenance, string> = {
  live: 'fetched from the source just now',
  cache: 'from a stored snapshot, not fetched just now',
  simulated: 'a stand-in scenario, not a real organization',
  synthetic: 'a generated signal, not a measurement',
};

const VARIANTS: Record<Provenance, string | undefined> = {
  live: styles.live,
  cache: styles.cache,
  simulated: styles.simulated,
  synthetic: styles.synthetic,
};

export interface ProvenanceBadgeProps {
  provenance: Provenance;
  /** Optional context, for example the source name or the snapshot age. */
  title?: string;
}

export function ProvenanceBadge({ provenance, title }: ProvenanceBadgeProps) {
  const glyph = GLYPHS[provenance];

  return (
    <span
      className={cx(styles.root, VARIANTS[provenance])}
      title={title ?? `${LABELS[provenance]}: ${DESCRIPTIONS[provenance]}`}
    >
      {glyph ? (
        <span className={styles.glyph} aria-hidden="true">
          {glyph}
        </span>
      ) : null}
      {LABELS[provenance]}
      <span className="visually-hidden">, {DESCRIPTIONS[provenance]}</span>
    </span>
  );
}
