'use client';

/**
 * Site and evidence queries.
 *
 * `/sites` returns an empty array before the first plan is published rather
 * than an error, so callers distinguish "loading" from "genuinely nothing yet"
 * on `data.length` rather than on an error state.
 */

import { useQuery } from '@tanstack/react-query';

import { fetchSiteEvidence, fetchSites } from '@/api/endpoints';
import { queryKeys } from '@/hooks/queryKeys';

export function useSites() {
  return useQuery({
    queryKey: queryKeys.sites(),
    queryFn: fetchSites,
  });
}

/**
 * Fused evidence for one site.
 *
 * Returns 404 until a plan exists, which is a real answer rather than a
 * transient failure, so it is not retried.
 */
export function useSiteEvidence(siteId: string | null) {
  return useQuery({
    queryKey: queryKeys.siteEvidence(siteId ?? ''),
    queryFn: () => fetchSiteEvidence(siteId as string),
    enabled: siteId !== null,
    retry: false,
  });
}
