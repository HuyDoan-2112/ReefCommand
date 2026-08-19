/**
 * The single source of truth for React Query cache keys.
 *
 * Keys live here rather than inline at each call site so that invalidation
 * after a re-plan cannot miss a cache entry because two files spelled the same
 * key differently.
 *
 * The hierarchy is deliberate: invalidating `queryKeys.plan()` also invalidates
 * every key nested under it, because React Query matches keys by prefix.
 */

export const queryKeys = {
  /** Everything derived from the current plan. */
  all: ['reefcommand'] as const,

  plan: () => [...queryKeys.all, 'plan'] as const,
  currentPlan: () => [...queryKeys.plan(), 'current'] as const,
  baselinePlan: () => [...queryKeys.plan(), 'baseline'] as const,
  latestSitePlan: (siteId: string) => [...queryKeys.plan(), 'site-latest', siteId] as const,

  sites: () => [...queryKeys.all, 'sites'] as const,
  siteEvidence: (siteId: string, planId?: string | null) =>
    [...queryKeys.sites(), siteId, 'evidence', planId ?? 'current'] as const,

  resources: () => [...queryKeys.all, 'resources'] as const,
  scenario: () => [...queryKeys.resources(), 'scenario'] as const,

  health: () => [...queryKeys.all, 'health'] as const,
  dataSources: () => [...queryKeys.health(), 'data-sources'] as const,

  trace: (planId: string) => [...queryKeys.all, 'trace', planId] as const,
  siteTrace: (planId: string, siteId: string) => [...queryKeys.trace(planId), siteId] as const,
} as const;
