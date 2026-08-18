/**
 * Shared presentational components.
 *
 * A component lives in its feature folder until a second feature needs it.
 * These are here because the mandatory rendering rules apply everywhere: the
 * simulated-data banner, provenance labelling, and the support-with-confidence
 * pairing must look and behave identically on every surface.
 */

export { Button } from './Button';
export type { ButtonProps } from './Button';

export { ConditionBadge } from './ConditionBadge';
export type { Condition, ConditionBadgeProps } from './ConditionBadge';

export { Panel } from './Panel';
export type { PanelProps } from './Panel';

export { ProvenanceBadge } from './ProvenanceBadge';
export type { ProvenanceBadgeProps } from './ProvenanceBadge';

export { SimulatedDataBanner } from './SimulatedDataBanner';
export type { SimulatedDataBannerProps } from './SimulatedDataBanner';

export { StatTile } from './StatTile';
export type { StatTileProps } from './StatTile';

export { SupportConfidenceBar } from './SupportConfidenceBar';
export type { SupportConfidenceBarProps } from './SupportConfidenceBar';
