import { CurrentPlan } from '@/features/plan';
import { CapacityPanel } from '@/features/resources';

/**
 * Resource Optimizer: the capacity in force, the control that changes it, and
 * the plan that capacity produces.
 *
 * Composition only.
 */
export default function OptimizerPage() {
  return (
    <>
      <CapacityPanel />
      <CurrentPlan />
    </>
  );
}
