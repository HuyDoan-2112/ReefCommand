import { OptimizerDashboard } from '@/features/resources';

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
      <OptimizerDashboard />
    </div>
  );
}
