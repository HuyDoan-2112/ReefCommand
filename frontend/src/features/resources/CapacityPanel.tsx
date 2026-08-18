'use client';

import { Button, Panel, ProvenanceBadge, SimulatedDataBanner } from '@/components';
import { useChangeScenario, useCurrentPlan } from '@/hooks/usePlan';
import { useScenario } from '@/hooks/useResources';
import { cx } from '@/lib/cx';

import styles from './CapacityPanel.module.css';

/**
 * The simulated capacity scenario, and the control that changes it.
 *
 * Changing the scenario is one of the two re-planning triggers. The backend
 * reruns only the optimizer, because a capacity change does not invalidate the
 * evidence or the policy decisions, and the response carries the new plan.
 *
 * The reference offers sliders for boats, teams, budget and travel time. Those
 * are not carried over: `PATCH /resources/scenario` takes a whole scenario id,
 * not per-resource values, so sliders would imply a control the backend does
 * not have. The real control is choosing between the defined scenarios.
 */

const SCENARIOS: ReadonlyArray<{ id: string; label: string; description: string }> = [
  {
    id: 'demo_default',
    label: 'Full capacity',
    description: 'Two boats, three dive teams, one operating day.',
  },
  {
    id: 'demo_boat_b_unavailable',
    label: 'Boat B out of service',
    description: 'One boat, three dive teams. Forces the optimizer to re-allocate.',
  },
];

export function CapacityPanel() {
  const { data: view, isPending, error } = useScenario();
  const { data: plan } = useCurrentPlan();
  const changeScenario = useChangeScenario();

  if (isPending)
    return (
      <Panel title="Capacity">
        <p className={styles.muted}>Loading...</p>
      </Panel>
    );
  if (error)
    return (
      <Panel title="Capacity">
        <p className={styles.muted}>Could not load the scenario: {error.message}</p>
      </Panel>
    );

  const scenario = view.scenario;
  const activeId = plan?.scenario_id ?? scenario.scenario_id;
  const boatsAvailable = scenario.boats.filter((boat) => boat.available !== false).length;
  const teamHours = scenario.dive_teams.reduce((sum, team) => sum + team.available_hours, 0);

  return (
    <div className={styles.root}>
      <SimulatedDataBanner text={view.banner} detail={scenario.label} />

      <Panel title="Capacity in force" hint={scenario.scenario_id}>
        <div className={styles.grid}>
          <div className={styles.metric}>
            <span className={styles.metricLabel}>Boats</span>
            <span className={styles.metricValue}>
              {boatsAvailable}
              <span className={styles.metricUnit}> / {scenario.boats.length}</span>
            </span>
            <ul className={styles.itemList}>
              {scenario.boats.map((boat) => (
                <li
                  key={boat.boat_id}
                  className={cx(styles.item, boat.available === false && styles.itemOut)}
                >
                  {boat.name}
                  <span className={styles.itemMeta}>
                    {boat.available === false
                      ? 'out of service'
                      : `${boat.operational_hours.toFixed(1)} h`}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className={styles.metric}>
            <span className={styles.metricLabel}>Dive teams</span>
            <span className={styles.metricValue}>
              {scenario.dive_teams.length}
              <span className={styles.metricUnit}> / {teamHours.toFixed(1)} h</span>
            </span>
            <ul className={styles.itemList}>
              {scenario.dive_teams.map((team) => (
                <li key={team.team_id} className={styles.item}>
                  {team.name}
                  <span className={styles.itemMeta}>
                    {team.diver_count} divers, {team.available_hours.toFixed(1)} h
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className={styles.metric}>
            <span className={styles.metricLabel}>Gear and budget</span>
            <ul className={styles.itemList}>
              <li className={styles.item}>
                Shade units<span className={styles.itemMeta}>{scenario.inventory.shade_units}</span>
              </li>
              <li className={styles.item}>
                Monitoring kits
                <span className={styles.itemMeta}>{scenario.inventory.monitoring_kits}</span>
              </li>
              <li className={styles.item}>
                Sampling kits
                <span className={styles.itemMeta}>{scenario.inventory.sampling_kits}</span>
              </li>
              <li className={styles.item}>
                Budget
                <span className={styles.itemMeta}>
                  ${scenario.budget_usd.toLocaleString('en-US')}
                </span>
              </li>
              <li className={styles.item}>
                Daylight<span className={styles.itemMeta}>{scenario.daylight_hours} h</span>
              </li>
            </ul>
            <div className={styles.provenance}>
              <ProvenanceBadge provenance={scenario.provenance} />
            </div>
          </div>
        </div>
      </Panel>

      <Panel title="Change capacity" hint="re-runs the optimizer only, not the investigators">
        <div className={styles.scenarioList}>
          {SCENARIOS.map((option) => {
            const isActive = option.id === activeId;
            return (
              <div key={option.id} className={cx(styles.scenario, isActive && styles.scenarioOn)}>
                <div className={styles.scenarioBody}>
                  <div className={styles.scenarioLabel}>
                    {option.label}
                    {isActive ? <span className={styles.activeTag}>In force</span> : null}
                  </div>
                  <div className={styles.scenarioDesc}>{option.description}</div>
                </div>
                <Button
                  variant={isActive ? 'ghost' : 'primary'}
                  size="small"
                  disabled={isActive || changeScenario.isPending}
                  onClick={() =>
                    changeScenario.mutate({
                      scenario_id: option.id,
                      description: option.label,
                    })
                  }
                >
                  {changeScenario.isPending ? 'Re-planning...' : isActive ? 'Active' : 'Apply'}
                </Button>
              </div>
            );
          })}
        </div>

        {changeScenario.isError ? (
          <p className={styles.error}>The capacity change failed: {changeScenario.error.message}</p>
        ) : null}

        {plan?.replan_trigger?.startsWith('resource_change') ? (
          <p className={styles.replanNote}>
            Plan re-planned from <code>{plan.replan_trigger}</code>
            {plan.replan_latency_ms !== null && plan.replan_latency_ms !== undefined
              ? ` in ${plan.replan_latency_ms} ms, measured server side.`
              : '.'}
          </p>
        ) : null}
      </Panel>
    </div>
  );
}
