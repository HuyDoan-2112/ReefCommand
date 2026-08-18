import { CurrentPlan } from '@/features/plan';
import { CapacityPanel } from '@/features/resources';

import styles from './page.module.css';

/**
 * Resource Optimizer: the capacity in force, the control that changes it, and
 * the plan that capacity produces.
 *
 * Composition only.
 */
export default function OptimizerPage() {
  return (
    <div className={styles.root}>
      <CapacityPanel mode="summary" />

      <div className={styles.callout}>
        <span aria-hidden="true">⚙️</span>
        <div>
          The Coordinator has already decided <strong>which</strong> policy-eligible actions are
          worth taking and <strong>why</strong>. The deterministic optimizer assigns the simulated
          boats, teams, equipment and budget under the current constraints.
        </div>
      </div>

      <div className={styles.optimizerGrid}>
        <CurrentPlan surface="optimizer" />
        <CapacityPanel mode="controls" />
      </div>
    </div>
  );
}
