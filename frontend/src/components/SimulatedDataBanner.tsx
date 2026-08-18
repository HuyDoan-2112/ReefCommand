import styles from './SimulatedDataBanner.module.css';

/**
 * States that the operational capacity behind a plan is simulated.
 *
 * Not dismissible, and deliberately has no collapsed state. `AGENTS.md` is
 * explicit that simulated fleet, personnel, inventory and budget data must be
 * labeled wherever they are displayed.
 *
 * The text is passed in rather than written here because the backend ships it
 * on the plan object (`scenario_banner`). That means the wording cannot drift
 * between the two, and a plan cannot arrive without one: `ResponsePlan`
 * requires the field.
 */

export interface SimulatedDataBannerProps {
  /** `scenario_banner` from the plan, or `banner` from the scenario view. */
  text: string;
  /** Optional extra context, for example which scenario is loaded. */
  detail?: string;
}

export function SimulatedDataBanner({ text, detail }: SimulatedDataBannerProps) {
  return (
    <aside className={styles.root} aria-label="Simulated data notice">
      <span className={styles.glyph} aria-hidden="true">
        ▲
      </span>
      <div className={styles.body}>
        <p className={styles.text}>{text}</p>
        {detail ? <p className={styles.detail}>{detail}</p> : null}
      </div>
    </aside>
  );
}
