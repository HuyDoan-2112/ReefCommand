'use client';

/**
 * Site and evidence queries.
 *
 * `/sites` returns an empty array before the first plan is published rather
 * than an error, so callers distinguish "loading" from "genuinely nothing yet"
 * on `data.length` rather than on an error state.
 */

import { useQueries, useQuery } from '@tanstack/react-query';

import { fetchSiteEvidence, fetchSites } from '@/api/endpoints';
import { queryKeys } from '@/hooks/queryKeys';

import { useCurrentPlan } from './usePlan';

export function useSites() {
  const currentPlan = useCurrentPlan();

  return useQuery({
    queryKey: queryKeys.sites(),
    queryFn: fetchSites,
    enabled: currentPlan.isSuccess,
  });
}

/**
 * Fused evidence for one site.
 *
 * Returns 404 until a plan exists, which is a real answer rather than a
 * transient failure, so it is not retried.
 */
export function useSiteEvidence(siteId: string | null, planId?: string | null) {
  return useQuery({
    queryKey: queryKeys.siteEvidence(siteId ?? '', planId),
    queryFn: () => fetchSiteEvidence(siteId as string, planId),
    enabled: siteId !== null && planId !== null,
    retry: false,
  });
}

/**
 * Fused evidence for every site currently visible on the map.
 *
 * The map uses this to draw optional evidence layers. Keeping the requests in
 * a hook preserves the same cache keys as the site detail surface, so opening a
 * site reuses data that the map already loaded.
 */
export function useSiteEvidenceBatch(siteIds: readonly string[]) {
  return useQueries({
    queries: siteIds.map((siteId) => ({
      queryKey: queryKeys.siteEvidence(siteId),
      queryFn: () => fetchSiteEvidence(siteId),
      retry: false,
    })),
  });
}
