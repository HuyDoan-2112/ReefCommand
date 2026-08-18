import {
  Button,
  ConditionBadge,
  Panel,
  ProvenanceBadge,
  SimulatedDataBanner,
  StatTile,
  SupportConfidenceBar,
} from '@/components';
import { CAUSES } from '@/types';

import styles from './page.module.css';

/**
 * A static gallery of the shared components.
 *
 * This exists so the primitives can be reviewed on their own, at the resolution
 * the demo runs at, before four feature surfaces are built on top of them. It
 * calls no API and holds no state: the values below are literals chosen to
 * exercise the awkward cases, not fetched data.
 *
 * Delete this route once the real surfaces exist.
 */

const SAMPLE = [
  { support: 0.82, confidence: 0.91, rationale: 'DHW 8.4 at alert level 2 for the past 6 days.' },
  {
    support: 0.61,
    confidence: 0.73,
    rationale: 'Lesion-pattern tissue loss reported on 3 colonies.',
  },
  {
    support: 0.13,
    confidence: 0.64,
    rationale: 'No turbidity reported and rainfall is below threshold.',
  },
  { support: 0.05, confidence: 0.78, rationale: 'No breakage, grounding, or close storm track.' },
];

export default function DesignPreviewPage() {
  const total = SAMPLE.reduce((sum, item) => sum + item.support, 0);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Design system preview</h1>
        <p className={styles.subtitle}>
          Shared components rendered with fixed sample values. Not connected to the API.
        </p>
      </header>

      <SimulatedDataBanner
        text="Simulated operational capacity. Not a real organization's fleet or personnel data."
        detail="This banner has no dismiss control by design."
      />

      <Panel title="Provenance" hint="colour is the secondary cue only">
        <div className={styles.row}>
          <ProvenanceBadge provenance="live" />
          <ProvenanceBadge provenance="cache" />
          <ProvenanceBadge provenance="simulated" />
          <ProvenanceBadge provenance="synthetic" />
        </div>
        <p className={styles.note}>
          Each kind carries a distinct glyph and its own word. Simulated and synthetic also take a
          dashed border, because those two must never be mistaken for measured values.
        </p>
      </Panel>

      <Panel title="Condition" hint="severity always states its basis">
        <div className={styles.row}>
          <ConditionBadge condition="good" basis="thermal evidence only, before fusion" />
          <ConditionBadge condition="warning" basis="thermal evidence only, before fusion" />
          <ConditionBadge condition="serious" basis="thermal evidence only, before fusion" />
          <ConditionBadge condition="critical" basis="thermal evidence only, before fusion" />
        </div>
      </Panel>

      <Panel
        title="Evidence support"
        hint={`four independent scores, summing to ${total.toFixed(2)}`}
      >
        <div className={styles.causeGrid}>
          {CAUSES.map((cause, index) => (
            <div key={cause} className={styles.causeCard}>
              <SupportConfidenceBar
                cause={cause}
                support={SAMPLE[index]!.support}
                confidence={SAMPLE[index]!.confidence}
                isDominant={SAMPLE[index]!.support >= 0.5}
                rationale={SAMPLE[index]!.rationale}
              />
            </div>
          ))}
        </div>
        <p className={styles.note}>
          These are support scores, not probabilities. They do not sum to 1 and the causes are not
          assumed independent, so they are never drawn as parts of a whole. Each bar is scaled
          against its own full 0 to 1 track.
        </p>
      </Panel>

      <Panel title="Confidence changes the reading" hint="same support, different situation">
        <div className={styles.causeGrid}>
          <div className={styles.causeCard}>
            <SupportConfidenceBar cause="thermal" support={0.8} confidence={0.3} />
          </div>
          <div className={styles.causeCard}>
            <SupportConfidenceBar cause="thermal" support={0.8} confidence={0.9} />
          </div>
        </div>
        <p className={styles.note}>
          Both read 0.80 support. The reference draws one bar per cause and cannot tell these apart.
        </p>
      </Panel>

      <div className={styles.statRow}>
        <StatTile
          label="🪸 Sites monitored"
          value={7}
          note="Mission: Iconic Reefs"
          decoration="🌊"
        />
        <StatTile
          label="🛥️ Boats committed"
          value={2}
          unit="/ 2"
          note="binding constraint"
          decoration="🛥️"
        />
        <StatTile label="🤿 Dive teams" value={2} unit="/ 3" note="one team idle" decoration="🤿" />
        <StatTile
          label="💵 Budget used"
          value="$1,700"
          unit="/ $10,000"
          note="simulated"
          decoration="💵"
        />
      </div>

      <Panel title="Buttons">
        <div className={styles.row}>
          <Button variant="primary">Recompute plan</Button>
          <Button variant="coral">Submit report</Button>
          <Button variant="ghost">Cancel</Button>
          <Button variant="primary" size="small">
            Small
          </Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
        </div>
        <p className={styles.note}>Tab through these to check focus states.</p>
      </Panel>
    </main>
  );
}
